# -*- coding: utf-8 -*-
"""
core/cache.py
Sistema de cache universal para todas as lojas.
Cada loja tem seu próprio ficheiro JSON, TTL diferenciado por tipo.

VERSÃO 4.7: TTL adaptativo (encontrados vs não encontrados)
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from config import CACHE_DIR, CACHE_TTL_FOUND_DAYS, CACHE_TTL_NOT_FOUND_DAYS


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
    
    def is_expired(self) -> bool:
        """
        Verifica se entrada expirou.
        TTL adaptativo: produtos encontrados vs não encontrados
        """
        try:
            cached_time = datetime.fromisoformat(self.timestamp)
            age = datetime.utcnow() - cached_time
            
            # TTL diferente baseado se produto foi encontrado ou não
            if self.url:
                # Produto encontrado: TTL mais longo (preços mudam devagar)
                max_age = timedelta(days=CACHE_TTL_FOUND_DAYS)
            else:
                # Produto não encontrado: TTL mais curto (stock pode chegar)
                max_age = timedelta(days=CACHE_TTL_NOT_FOUND_DAYS)
            
            return age > max_age
        
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
        
        # Verificar se expirou (usa TTL adaptativo)
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
        """Limpa todo o cache"""
        self._cache = {}
        self._dirty = True
    
    def remove_expired(self) -> int:
        """
        Remove todas as entradas expiradas.
        
        Returns:
            Número de entradas removidas
        """
        expired_refs = [
            ref for ref, entry in self._cache.items() 
            if entry.is_expired()
        ]
        
        for ref in expired_refs:
            del self._cache[ref]
        
        if expired_refs:
            self._dirty = True
        
        return len(expired_refs)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dict com estatísticas (total, encontrados, não encontrados, etc)
        """
        total = len(self._cache)
        found = sum(1 for entry in self._cache.values() if entry.url)
        not_found = total - found
        
        # Calcular idade média
        if total > 0:
            try:
                ages = []
                for entry in self._cache.values():
                    cached_time = datetime.fromisoformat(entry.timestamp)
                    age_hours = (datetime.utcnow() - cached_time).total_seconds() / 3600
                    ages.append(age_hours)
                avg_age_hours = sum(ages) / len(ages)
            except Exception:
                avg_age_hours = 0
        else:
            avg_age_hours = 0
        
        return {
            "store": self.store_name,
            "total_entries": total,
            "found": found,
            "not_found": not_found,
            "avg_age_hours": avg_age_hours,
            "cache_file": str(self.cache_file),
        }
    
    def __len__(self) -> int:
        """Número de entradas no cache"""
        return len(self._cache)
    
    def __repr__(self) -> str:
        return f"StoreCache(store={self.store_name}, entries={len(self)})"


# ============================================================================
# TESTES
# ============================================================================
if __name__ == "__main__":
    print("=== Teste de Cache ===\n")
    
    # Criar cache de teste
    cache = StoreCache("teste")
    
    # Adicionar entradas
    cache.put(
        ref_norm="ABC123",
        url="https://example.com/abc123",
        price_text="€ 45.99",
        price_num=45.99,
        confidence=0.95
    )
    
    cache.put(
        ref_norm="XYZ789",
        url=None,  # Não encontrado
        price_text=None,
        price_num=None,
        confidence=0.0
    )
    
    # Salvar
    cache.save()
    print(f"✅ Cache salvo: {cache.cache_file}")
    
    # Buscar
    entry = cache.get("ABC123")
    if entry:
        print(f"✅ Encontrado: {entry.ref_norm} → {entry.price_text}")
    
    # Estatísticas
    stats = cache.get_stats()
    print(f"\n📊 Estatísticas:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
