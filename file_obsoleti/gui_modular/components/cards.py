"""
Card Builder Component
"""

import flet as ft
from typing import Optional


class CardBuilder:
    """Build various card types"""
    
    @staticmethod
    def stat_card(
        title: str,
        value: str,
        icon: str,
        color: str = ft.Colors.BLUE_400
    ) -> ft.Card:
        """Build a statistics card"""
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, color=color, size=30),
                        ft.Text(value, size=32, weight=ft.FontWeight.BOLD)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(title, size=14, color=ft.Colors.ON_SURFACE_VARIANT)
                ], spacing=5),
                padding=20,
                width=200
            )
        )
    
    @staticmethod
    def info_card(
        title: str,
        content: str,
        icon: Optional[str] = None
    ) -> ft.Card:
        """Build an information card"""
        header = []
        if icon:
            header.append(ft.Icon(icon, size=20))
        header.append(ft.Text(title, size=16, weight=ft.FontWeight.BOLD))
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row(header, spacing=10),
                    ft.Divider(),
                    ft.Text(content, size=14)
                ], spacing=10),
                padding=20
            )
        )
