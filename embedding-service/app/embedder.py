"""Embedding model wrapper."""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class Embedder:
    """Embedding model wrapper supporting multiple backends."""
    
    def __init__(
        self,
        model_name: str = "Qwen3-Embedding-0.6B-ONNX",
        backend: str = "onnx",
        dimension: Optional[int] = None,
        device: str = "cpu"
    ):
        """初始化嵌入模型。
        
        Args:
            model_name: 模型名称或路径
            backend: 后端类型 (onnx, sentence_transformer, llama_cpp)
            dimension: 输出维度 (可选，默认使用模型默认值)
            device: 运行设备 (cpu, cuda, cuda:0 等)
        """
        self.model_name = model_name
        self.backend = backend
        self.dimension = dimension
        self.device = device
        self._model = None
        self._tokenizer = None
        self._session = None
        
    def _load_model(self):
        """加载嵌入模型。"""
        if self._model is not None:
            return
            
        if self.backend == "onnx":
            import os
            import onnxruntime as ort
            
            logger.info(f"加载 ONNX 模型: {self.model_name}")
            
            package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_name_safe = self.model_name.replace('/', '_')
            
            search_paths = [
                os.path.join(package_dir, model_name_safe),
                os.path.join(os.getcwd(), model_name_safe),
                os.path.join(package_dir, self.model_name),
                os.path.join(os.getcwd(), self.model_name),
            ]
            
            local_model_dir = None
            for path in search_paths:
                onnx_path = os.path.join(path, "model_int8.onnx")
                tokenizer_path = os.path.join(path, "tokenizer")
                if os.path.exists(onnx_path) and os.path.exists(tokenizer_path):
                    local_model_dir = path
                    break
            
            if local_model_dir is None:
                raise FileNotFoundError(
                    f"未找到模型 {self.model_name}，请确保模型目录存在。"
                    f"已搜索路径: {search_paths}"
                )
            
            onnx_path = os.path.join(local_model_dir, "model_int8.onnx")
            tokenizer_path = os.path.join(local_model_dir, "tokenizer")
            
            # 使用基础分词器
            logger.info("使用基础分词器进行推理")
            
            class BasicTokenizer:
                """基础分词器"""
                def __init__(self):
                    self.bos_token = "<s>"
                    self.eos_token = "</s>"
                    self.pad_token = "<pad>"
                    self.unk_token = "<unk>"
                    self.max_length = 512
                
                def __call__(self, texts, padding=True, truncation=True, max_length=512, return_tensors="np"):
                    """分词文本"""
                    tokenized = []
                    attention_masks = []
                    
                    for text in texts:
                        # 字符级分词
                        chars = list(text)[:max_length-2]  # 留出 bos 和 eos
                        
                        # 转换为 ID
                        token_ids = [0]  # bos
                        for char in chars:
                            char_id = ord(char) % 256 + 4  # 字符映射
                            token_ids.append(char_id)
                        token_ids.append(1)  # eos
                        
                        # 填充
                        if len(token_ids) < max_length:
                            token_ids += [2] * (max_length - len(token_ids))
                        else:
                            token_ids = token_ids[:max_length]
                        
                        # 注意力掩码
                        attention_mask = [1] * (len(chars) + 2)
                        if len(attention_mask) < max_length:
                            attention_mask += [0] * (max_length - len(attention_mask))
                        else:
                            attention_mask = attention_mask[:max_length]
                        
                        tokenized.append(token_ids)
                        attention_masks.append(attention_mask)
                    
                    result = {
                        "input_ids": np.array(tokenized, dtype=np.int64),
                        "attention_mask": np.array(attention_masks, dtype=np.int64)
                    }
                    
                    return result
            
            self._tokenizer = BasicTokenizer()
            logger.info("基础分词器初始化完成")
            
            # 配置 ONNX Runtime
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # 加载模型
            self._session = ort.InferenceSession(onnx_path, sess_options)
            logger.info(f"使用模型: model_int8.onnx, 路径: {onnx_path}")
            
            # 设置维度
            if self.dimension is None:
                self.dimension = 1024
                logger.info(f"ONNX 模型加载完成: {self.model_name}, 维度: {self.dimension}")
            
        elif self.backend == "sentence_transformer":
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
            if self.dimension:
                logger.info(f"模型加载完成: {self.model_name}, 维度: {self.dimension}")
            else:
                self.dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"模型加载完成: {self.model_name}, 维度: {self.dimension}")
        elif self.backend == "llama_cpp":
            from llama_cpp import Llama
            self._model = Llama(
                model_path=self.model_name,
                embedding=True,
                pooling_type=1
            )
            self.dimension = 1024
            logger.info(f"GGUF 模型加载完成: {self.model_name}")
        else:
            raise ValueError(f"未知后端: {self.backend}")
            
    def embed(self, texts: list[str]) -> list[list[float]]:
        """文本向量化。
        
        Args:
            texts: 要向量化的文本列表
            
        Returns:
            嵌入向量列表
        """
        self._load_model()
        
        if self.backend == "onnx":
            # 分词
            inputs = self._tokenizer(
                texts, 
                padding=True, 
                truncation=True, 
                max_length=512, 
                return_tensors="np"
            )
            
            input_ids = inputs['input_ids'].astype(np.int64)
            attention_mask = inputs['attention_mask'].astype(np.int64)
            
            ort_inputs = {
                'input_ids': input_ids,
                'attention_mask': attention_mask
            }
            
            # 获取模型输入信息
            input_names = [input.name for input in self._session.get_inputs()]
            logger.info(f"模型输入: {input_names}")
            
            # 添加缺失的输入
            batch_size, seq_length = input_ids.shape
            
            # 添加 position_ids
            if 'position_ids' in input_names:
                position_ids = np.arange(seq_length, dtype=np.int64)[None, :]
                position_ids = np.broadcast_to(position_ids, (batch_size, seq_length))
                ort_inputs['position_ids'] = position_ids
            
            # 添加 past_key_values
            has_past = any('past_key_values' in name for name in input_names)
            
            if has_past:
                logger.info("模型需要 past_key_values，准备空张量")
                # 为每层添加 past_key_values
                for i in range(32):  # 最多 32 层
                    key_name = f'past_key_values.{i}.key'
                    value_name = f'past_key_values.{i}.value'
                    
                    if key_name in input_names and value_name in input_names:
                        # 准备正确维度的空张量
                        ort_inputs[key_name] = np.zeros((batch_size, 8, 0, 128), dtype=np.float32)
                        ort_inputs[value_name] = np.zeros((batch_size, 8, 0, 128), dtype=np.float32)
            
            # 模型推理
            outputs = self._session.run(None, ort_inputs)
            token_embeddings = outputs[0]
            
            # 计算句子嵌入
            attention_mask_expanded = np.expand_dims(attention_mask, -1).astype(np.float32)
            attention_mask_expanded = np.broadcast_to(attention_mask_expanded, token_embeddings.shape)
            
            sum_embeddings = np.sum(token_embeddings * attention_mask_expanded, axis=1)
            sum_mask = np.clip(attention_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            sentence_embeddings = sum_embeddings / sum_mask
            
            # L2 归一化
            norms = np.linalg.norm(sentence_embeddings, axis=1, keepdims=True)
            sentence_embeddings = sentence_embeddings / np.maximum(norms, 1e-9)
            
            return sentence_embeddings.tolist()
            
        elif self.backend == "sentence_transformer":
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        elif self.backend == "llama_cpp":
            embeddings = []
            for text in texts:
                emb = self._model.embed(text)
                embeddings.append(emb)
            return embeddings
        else:
            raise ValueError(f"未知后端: {self.backend}")
            
    def get_dimension(self) -> int:
        """获取嵌入维度。"""
        self._load_model()
        return self.dimension

