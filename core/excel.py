# -*- coding: utf-8 -*-
"""
core/excel.py
Geração de Excel consolidado com múltiplas lojas lado-a-lado.
"""
from pathlib import Path
from typing import List, Dict, Optional

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .feed import FeedProduct


class ExcelBuilder:
    """
    Construtor de Excel multi-loja.
    
    Layout:
    | ID | Título | Ref Feed | Preço Feed | Loja1 Preço | Loja1 Dif% | Loja1 URL | Loja2 Preço | Loja2 Dif% | ...
    """
    
    def __init__(self, store_names: List[str]):
        """
        Args:
            store_names: Lista de nomes das lojas (ex: ["wrs", "omniaracing"])
        """
        self.store_names = store_names
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = "Comparador"
        
        # Estilos
        self._setup_styles()
    
    def _setup_styles(self):
        """Define estilos reutilizáveis"""
        # Header
        self.header_font = Font(bold=True, color="FFFFFF", size=11)
        self.header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        self.header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        
        # Borders
        thin_border = Side(border_style="thin", color="CCCCCC")
        self.border = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)
        
        # Formatação condicional
        self.green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        self.red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        self.gray_fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
    
    def _create_headers(self):
        """Cria linha de cabeçalhos"""
        headers = ["ID", "Título", "Ref Feed", "Preço Feed"]
        
        # Para cada loja: 3 colunas (Preço, Diferença %, URL)
        for store in self.store_names:
            store_name = store.upper()
            headers.extend([
                f"{store_name}\nPreço",
                f"{store_name}\nDif %",
                f"{store_name}\nURL"
            ])
        
        self.ws.append(headers)
        
        # Aplicar estilo ao header
        for col in range(1, len(headers) + 1):
            cell = self.ws.cell(1, col)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = self.header_align
            cell.border = self.border
        
        # Ajustar larguras (aproximadas)
        self.ws.column_dimensions['A'].width = 12  # ID
        self.ws.column_dimensions['B'].width = 35  # Título
        self.ws.column_dimensions['C'].width = 18  # Ref Feed
        self.ws.column_dimensions['D'].width = 12  # Preço Feed
        
        # Colunas das lojas
        col = 5  # Começa depois das 4 primeiras
        for _ in self.store_names:
            self.ws.column_dimensions[get_column_letter(col)].width = 12      # Preço
            self.ws.column_dimensions[get_column_letter(col + 1)].width = 10  # Dif%
            self.ws.column_dimensions[get_column_letter(col + 2)].width = 40  # URL
            col += 3
    
    def add_product_row(self, product: FeedProduct, 
                       store_results: Dict[str, Optional[Dict]]):
        """
        Adiciona linha de produto.
        
        Args:
            product: FeedProduct do feed
            store_results: Dict {store_name: result_dict ou None}
                result_dict tem: url, price_text, price_num, confidence
        """
        # Colunas base
        row_data = [
            product.id,
            product.title,
            product.ref_raw,
            product.price_text,
        ]
        
        # Para cada loja
        for store_name in self.store_names:
            result = store_results.get(store_name)
            
            if result and result.get("price_text"):
                # Produto encontrado
                price_text = result["price_text"]
                price_num = result.get("price_num")
                url = result.get("url", "")
                
                # Calcular diferença %
                diff_pct = None
                if product.price_num and price_num:
                    # Diferença: (preço_loja - preço_feed) / preço_feed
                    # Positivo = loja mais cara que tu (ganhas)
                    # Negativo = loja mais barata que tu (perdes)
                    diff_pct = (price_num - product.price_num) / product.price_num
                
                row_data.extend([price_text, diff_pct, url])
            else:
                # Produto não encontrado
                row_data.extend(["--", None, ""])
        
        # Adicionar linha
        row_num = self.ws.max_row + 1
        self.ws.append(row_data)
        
        # Aplicar formatação
        self._format_row(row_num, len(self.store_names))
    
    def add_product(self, product: FeedProduct, 
                   store_results: Dict[str, Optional[Dict]]):
        """
        Alias para add_product_row (compatibilidade).
        """
        return self.add_product_row(product, store_results)
    
    def to_buffer(self):
        """
        Retorna Excel como BytesIO buffer (para Streamlit download).
        
        Returns:
            BytesIO buffer com Excel
        """
        import io
        
        # Congelar primeira linha (headers)
        self.ws.freeze_panes = "A2"
        
        # Salvar em buffer
        buffer = io.BytesIO()
        self.wb.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    def _format_row(self, row_num: int, num_stores: int):
        """
        Aplica formatação a uma linha de dados.
        
        Args:
            row_num: Número da linha
            num_stores: Número de lojas
        """
        # Colunas base (A-D)
        for col in range(1, 5):
            cell = self.ws.cell(row_num, col)
            cell.border = self.border
            cell.alignment = Alignment(vertical="center")
        
        # Título (coluna B) - wrap text
        self.ws.cell(row_num, 2).alignment = Alignment(vertical="center", wrap_text=True)
        
        # Para cada loja (3 colunas por loja)
        col = 5
        for store_idx in range(num_stores):
            # Coluna preço
            price_cell = self.ws.cell(row_num, col)
            price_cell.border = self.border
            price_cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Coluna diferença %
            diff_cell = self.ws.cell(row_num, col + 1)
            diff_cell.border = self.border
            diff_cell.alignment = Alignment(horizontal="center", vertical="center")
            diff_cell.number_format = "0.0%"
            
            # Formatação condicional da diferença
            diff_value = diff_cell.value
            if isinstance(diff_value, (int, float)):
                if diff_value > 0:
                    # Positivo = loja mais cara que tu = VERDE (ganhas)
                    diff_cell.fill = self.green_fill
                elif diff_value < 0:
                    # Negativo = loja mais barata que tu = VERMELHO (perdes)
                    diff_cell.fill = self.red_fill
            elif diff_value is None and price_cell.value == "--":
                # Produto não encontrado = CINZA
                price_cell.fill = self.gray_fill
                diff_cell.fill = self.gray_fill
            
            # Coluna URL
            url_cell = self.ws.cell(row_num, col + 2)
            url_cell.border = self.border
            url_cell.alignment = Alignment(vertical="center")
            
            # Se tem URL, tornar hyperlink
            if url_cell.value and url_cell.value.startswith("http"):
                url_cell.hyperlink = url_cell.value
                url_cell.font = Font(color="0563C1", underline="single")
                url_cell.value = "🔗 Ver produto"
            
            col += 3
    
    def save(self, output_path: Path):
        """
        Salva workbook no disco.
        
        Args:
            output_path: Caminho para salvar Excel
        """
        # Garantir que diretório existe
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Congelar primeira linha (headers)
        self.ws.freeze_panes = "A2"
        
        # Salvar
        self.wb.save(output_path)


def build_excel(products: List[FeedProduct],
                store_names: List[str],
                results_by_store: Dict[str, Dict[str, Optional[Dict]]],
                output_path: Path) -> None:
    """
    Função conveniente para criar Excel completo.
    
    Args:
        products: Lista de FeedProduct
        store_names: Lista de nomes das lojas
        results_by_store: Dict {store_name: {ref_norm: result_dict}}
        output_path: Onde salvar o Excel
        
    Example:
        results_by_store = {
            "wrs": {
                "H085LR1X": {"url": "...", "price_text": "€365", "price_num": 365.0},
                "ABC123": None,  # Não encontrado
            },
            "omniaracing": {
                "H085LR1X": {"url": "...", "price_text": "€355", "price_num": 355.0},
            }
        }
    """
    builder = ExcelBuilder(store_names)
    builder._create_headers()
    
    for product in products:
        # Montar dict de resultados deste produto em cada loja
        store_results = {}
        for store_name in store_names:
            store_data = results_by_store.get(store_name, {})
            result = store_data.get(product.ref_norm)
            store_results[store_name] = result
        
        builder.add_product_row(product, store_results)
    
    builder.save(output_path)


def create_single_ref_excel(ref: str, ref_norm: str, your_price: float,
                           store_names: List[str], results: List[Dict]) -> object:
    """
    Cria Excel para busca rápida de uma única referência.
    
    Args:
        ref: Referência original
        ref_norm: Referência normalizada
        your_price: Preço do utilizador (opcional)
        store_names: Lista de lojas pesquisadas
        results: Lista de dicts com resultados
    
    Returns:
        BytesIO buffer com Excel
    """
    import io
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Busca Rápida"
    
    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    
    thin_border = Side(border_style="thin", color="CCCCCC")
    border = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)
    
    green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    gray_fill = PatternFill(start_color="F0F0F0", end_color="F0F0F0", fill_type="solid")
    
    # Headers
    headers = ["Loja", "Preço", "Diferença", "Confiança", "URL"]
    ws.append(headers)
    
    for col in range(1, 6):
        cell = ws.cell(1, col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = border
    
    # Larguras
    ws.column_dimensions['A'].width = 18  # Loja
    ws.column_dimensions['B'].width = 15  # Preço
    ws.column_dimensions['C'].width = 15  # Diferença
    ws.column_dimensions['D'].width = 12  # Confiança
    ws.column_dimensions['E'].width = 50  # URL
    
    # Dados
    for result in results:
        ws.append([
            result["Loja"],
            result["Preço"],
            result["Diferença"],
            result["Confiança"],
            result["URL"]
        ])
        
        row_num = ws.max_row
        
        # Aplicar borders
        for col in range(1, 6):
            cell = ws.cell(row_num, col)
            cell.border = border
            cell.alignment = Alignment(vertical="center")
        
        # Formatação condicional
        price_cell = ws.cell(row_num, 2)
        if result["Preço"] == "Não encontrado":
            price_cell.fill = gray_fill
        elif result["Preço"].startswith("Erro"):
            price_cell.fill = red_fill
        
        # URL como hyperlink
        url_cell = ws.cell(row_num, 5)
        if url_cell.value and url_cell.value.startswith("http"):
            url_cell.hyperlink = url_cell.value
            url_cell.font = Font(color="0563C1", underline="single")
            url_cell.value = "🔗 Ver produto"
    
    # Congelar headers
    ws.freeze_panes = "A2"
    
    # Salvar em buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return buffer


# ============================================================================
# TESTES
# ============================================================================
if __name__ == "__main__":
    print("=== Teste de Excel Builder ===\n")
    
    from .feed import FeedProduct
    from pathlib import Path
    
    # Produtos fake para teste
    products = [
        FeedProduct(
            "001", "Escape Mivv SR-1", "https://feed.com/p1",
            "€ 331.50", 331.50,
            "H.085.LR1X", "H085LR1X", ["H085LR1X"]
        ),
        FeedProduct(
            "002", "Travão Brembo Z04", "https://feed.com/p2",
            "€ 180.00", 180.00,
            "110A26310", "110A26310", ["110A26310"]
        ),
    ]
    
    # Resultados fake
    results = {
        "wrs": {
            "H085LR1X": {"url": "https://wrs.it/p1", "price_text": "€ 365.00", "price_num": 365.0},
            "110A26310": None,  # Não encontrado
        },
        "omniaracing": {
            "H085LR1X": {"url": "https://omnia.net/p1", "price_text": "€ 355.00", "price_num": 355.0},
            "110A26310": {"url": "https://omnia.net/p2", "price_text": "€ 175.00", "price_num": 175.0},
        },
    }
    
    # Gerar Excel
    output = Path("test_comparador.xlsx")
    build_excel(products, ["wrs", "omniaracing"], results, output)
    
    print(f"✅ Excel gerado: {output}")
    print("\nAbre o ficheiro para ver o resultado!")
    print("(Verde = concorrência mais cara, Vermelho = concorrência mais barata)")
