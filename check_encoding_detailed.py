#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import codecs
from pathlib import Path
import chardet

def check_file_encoding_detailed(file_path):
    results = {
        'path': file_path,
        'issues': []
    }
    
    try:
        with open(file_path, 'rb') as f:
            raw_content = f.read()
        
        if not raw_content:
            return results
        
        # 1. 检查BOM
        bom_info = None
        if raw_content.startswith(codecs.BOM_UTF8):
            bom_info = 'UTF-8 BOM'
            results['issues'].append({
                'type': 'bom',
                'detail': 'UTF-8 BOM detected'
            })
        elif raw_content.startswith(codecs.BOM_UTF16_LE):
            bom_info = 'UTF-16 LE BOM'
            results['issues'].append({
                'type': 'bom',
                'detail': 'UTF-16 LE BOM detected'
            })
        elif raw_content.startswith(codecs.BOM_UTF16_BE):
            bom_info = 'UTF-16 BE BOM'
            results['issues'].append({
                'type': 'bom',
                'detail': 'UTF-16 BE BOM detected'
            })
        
        # 2. 使用chardet检测编码
        detected = chardet.detect(raw_content)
        detected_encoding = detected.get('encoding', 'unknown')
        confidence = detected.get('confidence', 0)
        
        # 3. 尝试用UTF-8解码
        try:
            text_content = raw_content.decode('utf-8')
        except UnicodeDecodeError as e:
            results['issues'].append({
                'type': 'utf8_decode_error',
                'detail': f'Cannot decode as UTF-8: {e}',
                'detected_encoding': detected_encoding,
                'confidence': confidence
            })
            # 尝试用检测到的编码解码
            try:
                text_content = raw_content.decode(detected_encoding or 'latin-1')
            except:
                return results
        
        # 4. 检查替换字符
        replacement_count = text_content.count('\ufffd')
        if replacement_count > 0:
            results['issues'].append({
                'type': 'replacement_character',
                'detail': f'Found {replacement_count} replacement characters (U+FFFD)',
                'count': replacement_count
            })
        
        # 5. 检查非打印控制字符（排除常见的空白字符）
        control_chars = []
        for i, char in enumerate(text_content):
            code = ord(char)
            # 排除: \t (9), \n (10), \r (13), 以及正常可打印字符
            if code < 32 and code not in (9, 10, 13):
                control_chars.append({
                    'position': i,
                    'code': code,
                    'name': f'0x{code:02x}'
                })
            # 也检查一些其他问题字符
            elif code == 0x00:  # NULL
                control_chars.append({
                    'position': i,
                    'code': code,
                    'name': 'NULL'
                })
            elif code == 0xfeff:  # Zero Width No-Break Space (BOM character)
                control_chars.append({
                    'position': i,
                    'code': code,
                    'name': 'ZERO WIDTH NO-BREAK SPACE (BOM)'
                })
        
        if control_chars:
            results['issues'].append({
                'type': 'control_characters',
                'detail': f'Found {len(control_chars)} control characters',
                'characters': control_chars[:20]  # 只显示前20个
            })
        
        # 6. 检查Python文件的编码声明
        if file_path.endswith('.py'):
            first_lines = text_content.split('\n')[:3]
            has_coding_decl = any('coding' in line.lower() or 'encoding' in line.lower() for line in first_lines)
            
            # 检查文件中是否有非ASCII字符但没有编码声明
            has_non_ascii = any(ord(c) > 127 for c in text_content)
            if has_non_ascii and not has_coding_decl:
                results['issues'].append({
                    'type': 'missing_encoding_declaration',
                    'detail': 'Python file with non-ASCII characters but no encoding declaration'
                })
        
        # 7. 检查编码声明与实际编码是否一致
        if file_path.endswith('.py') and has_coding_decl:
            for line in first_lines:
                if 'coding' in line.lower() or 'encoding' in line.lower():
                    if 'utf-8' in line.lower() or 'utf8' in line.lower():
                        # 声明是UTF-8，检查实际是否是UTF-8
                        if detected_encoding and 'utf' not in detected_encoding.lower():
                            results['issues'].append({
                                'type': 'encoding_mismatch',
                                'detail': f'Declared UTF-8 but detected as {detected_encoding}',
                                'confidence': confidence
                            })
        
        # 8. 检查混合编码问题（同一文件中有不同编码的字符序列）
        # 这通常表现为某些字符看起来像乱码
        if detected_encoding and 'utf' not in detected_encoding.lower() and confidence > 0.7:
            results['issues'].append({
                'type': 'non_utf8_encoding',
                'detail': f'File detected as {detected_encoding} (confidence: {confidence:.2f})',
                'detected_encoding': detected_encoding,
                'confidence': confidence
            })
        
    except Exception as e:
        results['issues'].append({
            'type': 'error',
            'detail': str(e)
        })
    
    return results

def check_directory_detailed(directory):
    directory = Path(directory)
    all_results = []
    
    extensions = {'.py', '.json', '.qss', '.md', '.txt'}
    
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            result = check_file_encoding_detailed(str(file_path))
            if result['issues']:
                result['relative_path'] = str(file_path.relative_to(directory))
                all_results.append(result)
    
    return all_results

def main():
    target_dir = r'd:\bot_workspace\FTK_bot\FTK_Claw_Bot\ftk_claw_bot'
    
    print(f"正在详细检查目录: {target_dir}")
    print("=" * 80)
    
    results = check_directory_detailed(target_dir)
    
    if not results:
        print("\n✓ 所有文件编码正常，未发现编码问题")
        return
    
    print(f"\n发现 {len(results)} 个文件存在编码问题:\n")
    
    for idx, result in enumerate(results, 1):
        print(f"{idx}. {result['relative_path']}")
        print(f"   完整路径: {result['path']}")
        
        for issue in result['issues']:
            issue_type = issue['type']
            detail = issue['detail']
            
            if issue_type == 'bom':
                print(f"   [BOM] {detail}")
            elif issue_type == 'utf8_decode_error':
                print(f"   [UTF-8解码错误] {detail}")
            elif issue_type == 'replacement_character':
                print(f"   [替换字符] {detail}")
            elif issue_type == 'control_characters':
                print(f"   [控制字符] {detail}")
                for char in issue.get('characters', []):
                    print(f"      位置 {char['position']}: {char['name']}")
            elif issue_type == 'missing_encoding_declaration':
                print(f"   [缺少编码声明] {detail}")
            elif issue_type == 'encoding_mismatch':
                print(f"   [编码不匹配] {detail}")
            elif issue_type == 'non_utf8_encoding':
                print(f"   [非UTF-8编码] {detail}")
            else:
                print(f"   [{issue_type}] {detail}")
        
        print()
    
    print("=" * 80)
    print(f"总计: {len(results)} 个文件存在编码问题")

if __name__ == '__main__':
    main()
