"""页面数据提取器"""
from typing import Dict, Any, List, Optional
from playwright.async_api import Page


class DataExtractor:
    """页面数据提取器，用于从网页中提取结构化数据"""

    @staticmethod
    async def extract_page_structure(page: Page, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """提取页面结构信息"""
        config = config or {}
        interactive_weight = config.get('interactive_weight', 100)
        min_area = config.get('min_area', 100)
        include_duplicates = config.get('include_duplicates', False)

        await page.wait_for_load_state("domcontentloaded")
        title = await page.title()

        # 使用 JavaScript 提取页面元素
        raw_elements = await page.evaluate('''() => {
            const elements = [];
            const allElements = document.querySelectorAll('*');

            function generateSelector(el) {
                if (el.id) return '#' + el.id;
                if (el.className && typeof el.className === 'string') {
                    return '.' + el.className.split(' ').filter(c => c).join('.');
                }
                return el.tagName.toLowerCase();
            }

            allElements.forEach((el) => {
                const rect = el.getBoundingClientRect();
                const text = el.textContent.trim();

                if (text && rect.width > 0 && rect.height > 0) {
                    const tag = el.tagName.toLowerCase();
                    elements.push({
                        tag: tag,
                        type: el.type || '',
                        action_type: tag === 'a' || tag === 'button' ? 'click' : tag === 'input' ? 'fill' : 'none',
                        text: text,
                        selector: generateSelector(el),
                        location: {
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        },
                        is_interactive: ['a', 'button', 'input', 'select', 'textarea'].includes(tag),
                        href: el.href || '',
                        name: el.name || '',
                        placeholder: el.placeholder || ''
                    });
                }
            });
            return elements;
        }''')

        raw_elements = raw_elements or []

        # 过滤并计算权重
        elements_with_weight = []
        for el in raw_elements:
            loc = el['location']
            area = loc['width'] * loc['height']
            if area < min_area:
                continue
            el['weight'] = (interactive_weight if el['is_interactive'] else 0) + area
            elements_with_weight.append(el)

        # 按权重排序
        elements_with_weight.sort(key=lambda x: x['weight'], reverse=True)

        # 按文本分组
        text_groups = {}
        for el in elements_with_weight:
            text_groups.setdefault(el['text'], []).append(el)

        # 构建结果元素列表
        result_elements = []
        for group_id, (text, group) in enumerate(text_groups.items(), 1):
            group.sort(key=lambda x: x['weight'], reverse=True)
            for i, el in enumerate(group):
                result_elements.append({
                    'id': len(result_elements) + 1,
                    'tag': el['tag'],
                    'type': el['type'],
                    'action_type': el['action_type'],
                    'text': el['text'],
                    'selector': el['selector'],
                    'location': el['location'],
                    'is_interactive': el['is_interactive'],
                    'weight': el['weight'],
                    'is_primary': (i == 0),
                    'duplicate_count': len(group),
                    'text_group_id': f"g_{group_id}",
                    'href': el.get('href', ''),
                    'name': el.get('name', ''),
                    'placeholder': el.get('placeholder', '')
                })

        # 过滤重复元素
        if not include_duplicates:
            result_elements = [e for e in result_elements if e['is_primary']]

        # 重新编号
        for i, el in enumerate(result_elements, 1):
            el['id'] = i

        interactive_count = sum(1 for e in result_elements if e['is_interactive'])
        forms = await DataExtractor.extract_forms(page)

        return {
            'url': page.url,
            'title': title,
            'elements': result_elements,
            'forms': forms,
            'summary': {
                'total': len(result_elements),
                'interactive': interactive_count,
                'unique_text': len(text_groups),
                'form_count': len(forms)
            }
        }

    @staticmethod
    async def extract_forms(page: Page) -> List[Dict[str, Any]]:
        """提取页面表单信息"""
        forms = await page.evaluate('''() => {
            const forms = [];
            document.querySelectorAll('form').forEach((form, index) => {
                const fields = [];
                form.querySelectorAll('input, select, textarea').forEach(field => {
                    fields.push({
                        tag: field.tagName.toLowerCase(),
                        type: field.type || '',
                        name: field.name || '',
                        placeholder: field.placeholder || '',
                        selector: field.id ? '#' + field.id :
                                 field.className ? '.' + field.className.split(' ').filter(c => c).join('.') :
                                 field.tagName.toLowerCase()
                    });
                });
                forms.push({
                    selector: form.id ? '#' + form.id : 'form:nth-of-type(' + (index + 1) + ')',
                    action: form.action || '',
                    method: form.method || 'GET',
                    fields: fields
                });
            });
            return forms;
        }''')
        return forms or []

    @staticmethod
    async def extract_by_selectors(page: Page, selectors: List[Dict[str, str]]) -> Dict[str, Any]:
        """根据选择器提取数据"""
        data = {}
        for item in selectors:
            name = item.get("name")
            selector = item.get("selector")
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    texts = [(await el.text_content()).strip() for el in elements]
                    data[name] = texts[0] if len(texts) == 1 else texts
                else:
                    data[name] = None
            except Exception:
                data[name] = None
        return data
