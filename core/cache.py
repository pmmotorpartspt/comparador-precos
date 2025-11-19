# -*- coding: utf-8 -*-
"""
core/cache.py
Sistema de cache universal para todas as lojas.
Cada loja tem seu próprio ficheiro JSON, TTL de 24h.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from config import CACHE_DIR, CACHE_TTL_HOURS


@dataclass
class CacheEntry:
    """Entrada de cache para um produto"""
    ref_norm: str              # Referência normalizada (chave)
    url: Optional[str]         # URL do produto (None se não encontrado)
    price_text: Optional[str]  # Preço como string (ex: "€ 365.50")
    price_num: Optional[float] # Preço como número (para cálculos)
    timestamp: str             # ISO timestamp de quando foi guardado
    confidence: float = 1.0    # Confiança na validação (0.0 a 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário (para JSON)"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Cria CacheEntry a partir de dicionário"""
        return cls(**data)
    
    def is_expired(self, ttl_hours: int = CACHE_TTL_HOURS) -> bool:
        """Verifica se entrada expirou"""
        try:
            cached_time = datetime.fromisoformat(self.timestamp)
            age = datetime.utcnow() - cached_time
            return age > timedelta(hours=ttl_hours)
        except Exception:
            return True  # Se erro ao parsear data, considerar expirado


class StoreCache:
    """
    Cache para uma loja específica.
    Cada loja tem seu ficheiro JSON independente.
    """
    
    def __init__(self, store_name: str):
        """
        Args:
            store_name: Nome da loja (ex: "wrs", "omniaracing")
        """
        self.store_name = store_name
        self.cache_file = CACHE_DIR / f"{store_name}_cache.json"
        self._cache: Dict[str, CacheEntry] = {}
        self._dirty = False  # Flag para saber se precisa salvar
        
        # Carregar cache existente
        self._load()
    
    def _load(self) -> None:
        """Carrega cache do disco"""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Converter dicionários para CacheEntry
            for ref_norm, entry_dict in data.items():
                # Adicionar campo confidence se não existir (compatibilidade)
                if 'confidence' not in entry_dict:
                    entry_dict['confidence'] = 1.0
                self._cache[ref_norm] = CacheEntry.from_dict(entry_dict)
        
        except Exception as e:
            print(f"[AVISO] Erro ao carregar cache de {self.store_name}: {e}")
            self._cache = {}
    
    def save(self) -> None:
        """Salva cache no disco (só se houve mudanças)"""
        if not self._dirty:
            return
        
        try:
            # Converter CacheEntry para dicionários
            data = {ref: entry.to_dict() for ref, entry in self._cache.items()}
            
            # Garantir que diretório existe
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Salvar JSON com indentação para legibilidade
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self._dirty = False
        
        except Exception as e:
            print(f"[ERRO] Não foi possível salvar cache de {self.store_name}: {e}")
    
    def get(self, ref_norm: str) -> Optional[CacheEntry]:
        """
        Busca entrada no cache.
        
        Args:
            ref_norm: Referência normalizada
            
        Returns:
            CacheEntry se encontrado e válido, None se não existe ou expirou
        """
        entry = self._cache.get(ref_norm)
        
        if entry is None:
            return None
        
        # Verificar se expirou
        if entry.is_expired():
            # Remover entrada expirada
            del self._cache[ref_norm]
            self._dirty = True
            return None
        
        return entry
    
    def put(self, ref_norm: str, url: Optional[str], price_text: Optional[str], 
            price_num: Optional[float], confidence: float = 1.0) -> None:
        """
        Adiciona ou atualiza entrada no cache.
        
        Args:
            ref_norm: Referência normalizada
            url: URL do produto (None se não encontrado)
            price_text: Preço formatado
            price_num: Preço numérico
            confidence: Confiança na validação (0.0 a 1.0)
        """
        entry = CacheEntry(
            ref_norm=ref_norm,
            url=url,
            price_text=price_text,
            price_num=price_num,
            timestamp=datetime.utcnow().isoformat(timespec='seconds'),
            confidence=confidence
        )
        
        self._cache[ref_norm] = entry
        self._dirty = True
    
    def clear(self) -> None:
        """Limpa todo o cache (útil para --refresh)"""
        self._cache = {}
        self._dirty = True
    
    def clear_expired(self) -> int:
        """
        Remove entradas expiradas do cache.
        
        Returns:
            Número de entradas removidas
        """
        expired_keys = [
            ref for ref, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self._dirty = True
        
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dict com: total, found (com URL), not_found (sem URL), expired
        """
        total = len(self._cache)
        found = sum(1 for e in self._cache.values() if e.url is not None)
        not_found = total - found
        
        # Contar expirados (sem remover)
        expired = sum(1 for e in self._cache.values() if e.is_expired())
        
        return {
            "total": total,
            "found": found,
            "not_found": not_found,
            "expired": expired,
            "store": self.store_name
        }
    
    def __enter__(self):
        """Context manager: permite usar 'with cache: ...'"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: salva automaticamente ao sair"""
        self.save()


# ============================================================================
# TESTES
# ============================================================================
if __name__ == "__main__":
    print("=== Teste de Cache ===\n")
    
    # Criar cache de teste
    cache = StoreCache("test_store")
    
    # Adicionar entrada
    cache.put("H085LR1X", "https://example.com/product", "€ 365.50", 365.50, 1.0)
    print("Entrada adicionada")
    
    # Buscar entrada
    entry = cache.get("H085LR1X")
    if entry:
        print(f"Entrada encontrada: URL={entry.url}, Preço={entry.price_text}")
    
    # Estatísticas
    stats = cache.stats()
    print(f"\nEstatísticas: {stats}")
    
    # Salvar
    cache.save()
    print("\nCache salvo!")
    
    # Limpar ficheiro de teste
    import os
    test_file = CACHE_DIR / "test_store_cache.json"
    if test_file.exists():
        os.remove(test_file)
        print("Ficheiro de teste removido")
