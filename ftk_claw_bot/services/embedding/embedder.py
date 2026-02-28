# -*- coding: utf-8 -*-
import os
import logging
from typing import Optional
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class Embedder:
    """Embedding 模型包装器"""
    
    def __init__(self, model_path: str, dimension: Optional[int] = None):
        self.model_path = model_path
        self.dimension = dimension
        self._session = None
        self._tokenizer = None
    
    def _load_model(self):
        if self._session is not None:
            return
        
        onnx_path = os.path.join(self.model_path, "model_int8.onnx")
        
        if not os.path.exists(onnx_path):
            raise FileNotFoundError(f"模型文件不存在: {onnx_path}")
        
        logger.info(f"加载 ONNX 模型: {onnx_path}")
        
        self._tokenizer = self._create_basic_tokenizer()
        logger.info("基础分词器初始化完成")
        
        import onnxruntime as ort
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        self._session = ort.InferenceSession(onnx_path, sess_options)
        logger.info(f"ONNX 模型加载完成: {onnx_path}")
        
        if self.dimension is None:
            self.dimension = 1024
    
    def _create_basic_tokenizer(self):
        class BasicTokenizer:
            def __init__(self):
                self.max_length = 512
            
            def __call__(self, texts, padding=True, truncation=True, max_length=512, return_tensors="np"):
                tokenized = []
                attention_masks = []
                
                for text in texts:
                    chars = list(text)[:max_length-2]
                    
                    token_ids = [0]
                    for char in chars:
                        char_id = ord(char) % 256 + 4
                        token_ids.append(char_id)
                    token_ids.append(1)
                    
                    if len(token_ids) < max_length:
                        token_ids += [2] * (max_length - len(token_ids))
                    else:
                        token_ids = token_ids[:max_length]
                    
                    attention_mask = [1] * (len(chars) + 2)
                    if len(attention_mask) < max_length:
                        attention_mask += [0] * (max_length - len(attention_mask))
                    else:
                        attention_mask = attention_mask[:max_length]
                    
                    tokenized.append(token_ids)
                    attention_masks.append(attention_mask)
                
                return {
                    "input_ids": np.array(tokenized, dtype=np.int64),
                    "attention_mask": np.array(attention_masks, dtype=np.int64)
                }
        
        return BasicTokenizer()
    
    def embed(self, texts: list) -> list:
        self._load_model()
        
        inputs = self._tokenizer(
            texts, padding=True, truncation=True, max_length=512, return_tensors="np"
        )
        
        input_ids = inputs['input_ids'].astype(np.int64)
        attention_mask = inputs['attention_mask'].astype(np.int64)
        
        ort_inputs = {
            'input_ids': input_ids,
            'attention_mask': attention_mask
        }
        
        input_names = [inp.name for inp in self._session.get_inputs()]
        batch_size, seq_length = input_ids.shape
        
        if 'position_ids' in input_names:
            position_ids = np.arange(seq_length, dtype=np.int64)[None, :]
            position_ids = np.broadcast_to(position_ids, (batch_size, seq_length))
            ort_inputs['position_ids'] = position_ids
        
        has_past = any('past_key_values' in name for name in input_names)
        if has_past:
            for i in range(32):
                key_name = f'past_key_values.{i}.key'
                value_name = f'past_key_values.{i}.value'
                if key_name in input_names and value_name in input_names:
                    ort_inputs[key_name] = np.zeros((batch_size, 8, 0, 128), dtype=np.float32)
                    ort_inputs[value_name] = np.zeros((batch_size, 8, 0, 128), dtype=np.float32)
        
        outputs = self._session.run(None, ort_inputs)
        token_embeddings = outputs[0]
        
        attention_mask_expanded = np.expand_dims(attention_mask, -1).astype(np.float32)
        attention_mask_expanded = np.broadcast_to(attention_mask_expanded, token_embeddings.shape)
        
        sum_embeddings = np.sum(token_embeddings * attention_mask_expanded, axis=1)
        sum_mask = np.clip(attention_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
        sentence_embeddings = sum_embeddings / sum_mask
        
        norms = np.linalg.norm(sentence_embeddings, axis=1, keepdims=True)
        sentence_embeddings = sentence_embeddings / np.maximum(norms, 1e-9)
        
        return sentence_embeddings.tolist()
    
    def get_dimension(self) -> int:
        self._load_model()
        return self.dimension
