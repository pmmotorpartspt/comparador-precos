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
    Construtor de Excel consolidado com múltiplas lojas.

    Estrutura:
        Colunas fixas:
            A: ID
            B: Título
            C: Ref Feed
            D: Preço Feed

        Para cada loja (N):
            3 colunas:
                Preço Loja N
                Dif % Loja N vs Feed
                Link Loja N
    """

    def __init__(self, store_names: List[str]):
        """
        Args:
            store_names: Lista de nomes das lojas, na ordem em que devem aparecer.
        """
        self.store_names = store_names
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = "Comparador"

        # Estilos base
        self.header_font = Font(bold=True)
        self.center_alignment = Alignment(horizontal="center", vertical="center")
        self.wrap_alignment = Alignment(wrap_text=True, vertical="center")

        # Bordas
        thin_border = Side(border_style="thin", color="CCCCCC")
        self.border = Border(
            left=thin_border,
            right=thin_border,
            top=thin_border,
            bottom=thin_border,
        )

        # Formatação condicional
        self.green_fill = PatternFill(
            start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
        )
        self.red_fill = PatternFill(
            start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"
        )
        self.gray_fill = PatternFill(
            start_color="F0F0F0", end_color="F0F0F0", fill_type="solid"
        )

        self._create_headers()

    def _create_headers(self):
        """Cria linha de cabeçalhos"""
        headers = ["ID", "Título", "Ref Feed", "Preço Feed"]

        # Para cada loja: 3 colunas (Preço, Dif%, Link)
        for store_name in self.store_names:
            headers.extend([f"{store_name} Preço", f"{store_name} Dif%", f"{store_name} Link"])

        self.ws.append(headers)

        # Aplicar estilo aos cabeçalhos
        for col_idx, _ in enumerate(headers, start=1):
            cell = self.ws.cell(row=1, column=col_idx)
            cell.font = self.header_font
            cell.alignment = self.center_alignment
            cell.border = self.border

        # Larguras base das colunas
        self.ws.column_dimensions["A"].width = 14  # ID
        self.ws.column_dimensions["B"].width = 60  # Título
        self.ws.column_dimensions["C"].width = 20  # Ref Feed
        self.ws.column_dimensions["D"].width = 14  # Preço Feed

        # Lojas
        col = 5
        for _ in self.store_names:
            self.ws.column_dimensions[get_column_letter(col)].width = 16  # Preço
            self.ws.column_dimensions[get_column_letter(col + 1)].width = 10  # Dif%
            self.ws.column_dimensions[get_column_letter(col + 2)].width = 18  # Link
            col += 3

    def add_product_row(
        self, product: FeedProduct, store_results: Dict[str, Optional[Dict]]
    ):
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

    def add_product(
        self, product: FeedProduct, store_results: Dict[str, Optional[Dict]]
    ):
        """
        Alias para add_product_row (por compatibilidade).
        """
        self.add_product_row(product, store_results)

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
        self.ws.cell(row_num, 2).alignment = Alignment(
            vertical="center", wrap_text=True
        )

        # Para cada loja (3 colunas por loja)
        col = 5
        for store_idx in range(num_stores):
            # Coluna preço
            price_cell = self.ws.cell(row_num, col)
            price_cell.border = self.border
            price_cell.alignment = Alignment(
                horizontal="center", vertical="center"
            )

            # Coluna diferença %
            diff_cell = self.ws.cell(row_num, col + 1)
            diff_cell.border = self.border
            diff_cell.alignment = Alignment(
                horizontal="center", vertical="center"
            )
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
            elif diff_value is None and price_cell.value not in (None, "", "--"):
                # Preço textual presente mas sem valor numérico parseável: marcar como N/A
                diff_cell.value = "N/A"
                diff_cell.alignment = Alignment(
                    horizontal="center", vertical="center"
                )

            # Coluna URL
            url_cell = self.ws.cell(row_num, col + 2)
            url_cell.border = self.border
            url_cell.alignment = Alignment(vertical="center")

            # Se tem URL, tornar hyperlink
            if url_cell.value and isinstance(url_cell.value, str) and url_cell.value.startswith(
                "http"
            ):
                url_cell.hyperlink = url_cell.value
                url_cell.font = Font(color="0563C1", underline="single")
                url_cell.value = "🔗 Ver produto"

            col += 3

    def save(self, output_path: Path):
        """
        Guarda o Excel num ficheiro.

        Args:
            output_path: Caminho completo para o ficheiro .xlsx
        """
        # Congelar primeira linha (headers)
        self.ws.freeze_panes = "A2"

        # Salvar
        self.wb.save(output_path)


def build_excel(
    products: List[FeedProduct],
    store_names: List[str],
    results_by_store: Dict[str, Dict[str, Optional[Dict]]],
    output_path: Path,
) -> None:
    """
    Função conveniente para criar Excel completo.

    Args:
        products: Lista de FeedProduct
        store_names: Lista de nomes das lojas
        results_by_store:
            Dict {store_name: Dict {ref_norm: result_dict}}
        output_path: Caminho de saída do ficheiro .xlsx
    """
    builder = ExcelBuilder(store_names)

    for product in products:
        store_results: Dict[str, Optional[Dict]] = {}
        for store_name in store_names:
            store_dict = results_by_store.get(store_name, {})
            store_results[store_name] = store_dict.get(product.ref_norm)

        builder.add_product_row(product, store_results)

    builder.save(output_path)
