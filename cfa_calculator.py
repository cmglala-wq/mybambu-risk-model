"""
Cash Flow Affordability (CFA) Calculator
=========================================
Implementación de la métrica CFA para evaluar capacidad de pago basada en
balance diario vs. biweekly parcel del usuario.

Dataset requerido: 6 meses de transacciones con:
- daily_balance
- daily_income
- daily_expenses
- biweekly_parcel (según tier)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, Tuple
import json

# Configuración de estilo
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)


class CFACalculator:
    """
    Calculadora de Cash Flow Affordability (CFA).

    Mide la capacidad de pago del usuario basada en su habilidad para
    cubrir el biweekly parcel en cualquier día del periodo de análisis.
    """

    def __init__(self, data: pd.DataFrame, biweekly_parcel: float):
        """
        Inicializa el calculador CFA.

        Args:
            data: DataFrame con columnas ['date', 'daily_balance', 'daily_income', 'daily_expenses']
            biweekly_parcel: Monto del pago quincenal según tier del usuario
        """
        self.data = data.copy()
        self.data['date'] = pd.to_datetime(self.data['date'])
        self.data = self.data.sort_values('date').reset_index(drop=True)
        self.biweekly_parcel = biweekly_parcel

        # Calcular daily_net si no existe
        if 'daily_net' not in self.data.columns:
            self.data['daily_net'] = self.data['daily_income'] - self.data['daily_expenses']

        # Validar dataset
        self._validate_data()

    def _validate_data(self):
        """Valida que el dataset tenga al menos 90 días de datos."""
        if len(self.data) < 90:
            raise ValueError(f"Dataset debe tener al menos 90 días. Actual: {len(self.data)} días")

        required_cols = ['date', 'daily_balance', 'daily_income', 'daily_expenses']
        missing = set(required_cols) - set(self.data.columns)
        if missing:
            raise ValueError(f"Faltan columnas requeridas: {missing}")

    def calculate_can_pay(self) -> pd.Series:
        """
        Calcula can_pay para cada día.

        Returns:
            Serie booleana: 1 si daily_balance >= biweekly_parcel, 0 si no
        """
        self.data['can_pay'] = (self.data['daily_balance'] >= self.biweekly_parcel).astype(int)
        return self.data['can_pay']

    def calculate_temporal_metrics(self) -> Dict[str, float]:
        """
        Calcula métricas temporales pct_90 y pct_6m.

        Returns:
            Dict con pct_90, pct_6m, y CFA final
        """
        # Asegurar que can_pay esté calculado
        if 'can_pay' not in self.data.columns:
            self.calculate_can_pay()

        # pct_90: últimos 90 días
        last_90_days = self.data.tail(90)
        pct_90 = last_90_days['can_pay'].sum() / 90

        # pct_6m: todos los datos (hasta 6 meses)
        total_days_6m = len(self.data)
        pct_6m = self.data['can_pay'].sum() / total_days_6m

        # CFA ponderado: 70% últimos 90 días + 30% histórico 6 meses
        cfa_score = (pct_90 * 0.70) + (pct_6m * 0.30)

        return {
            'pct_90': round(pct_90, 4),
            'pct_6m': round(pct_6m, 4),
            'cfa_score': round(cfa_score, 4),
            'total_days': total_days_6m,
            'biweekly_parcel': self.biweekly_parcel
        }

    def calculate_cfa(self) -> Dict:
        """
        Calcula CFA completo con todas las métricas.

        Returns:
            Dict con métricas CFA y análisis adicional
        """
        metrics = self.calculate_temporal_metrics()

        # Análisis adicional
        last_90 = self.data.tail(90)

        # Días consecutivos con capacidad de pago (últimos 90 días)
        can_pay_series = last_90['can_pay'].values
        max_consecutive = self._max_consecutive_ones(can_pay_series)

        # Estadísticas de balance
        balance_stats = {
            'avg_balance': round(self.data['daily_balance'].mean(), 2),
            'min_balance': round(self.data['daily_balance'].min(), 2),
            'max_balance': round(self.data['daily_balance'].max(), 2),
            'std_balance': round(self.data['daily_balance'].std(), 2),
        }

        # Estadísticas de flujo neto
        net_stats = {
            'avg_daily_net': round(self.data['daily_net'].mean(), 2),
            'positive_days_pct': round((self.data['daily_net'] > 0).sum() / len(self.data), 4),
        }

        return {
            **metrics,
            'max_consecutive_can_pay_90d': max_consecutive,
            'balance_stats': balance_stats,
            'net_stats': net_stats,
            'risk_tier': self._determine_risk_tier(metrics['cfa_score']),
            'recommendation': self._get_recommendation(metrics['cfa_score'])
        }

    def _max_consecutive_ones(self, arr: np.ndarray) -> int:
        """Calcula la secuencia máxima de 1s consecutivos."""
        max_count = 0
        current_count = 0
        for val in arr:
            if val == 1:
                current_count += 1
                max_count = max(max_count, current_count)
            else:
                current_count = 0
        return max_count

    def _determine_risk_tier(self, cfa_score: float) -> str:
        """Determina el tier de riesgo basado en CFA score."""
        if cfa_score >= 0.70:
            return "Tier 3 (Premium) - CFA 70-100%"
        elif cfa_score >= 0.60:
            return "Tier 2 (Standard) - CFA 60-69%"
        elif cfa_score >= 0.50:
            return "Tier 1 (Starter) - CFA 50-59%"
        else:
            return "Denied - CFA <50%"

    def _get_recommendation(self, cfa_score: float) -> str:
        """Genera recomendación de underwriting basada en CFA."""
        if cfa_score >= 0.70:
            return "APPROVE - Alta capacidad de pago. Elegible para Tier 3 ($200, 90 días)."
        elif cfa_score >= 0.60:
            return "APPROVE - Buena capacidad de pago. Elegible para Tier 2 ($150, 60 días)."
        elif cfa_score >= 0.50:
            return "CONDITIONAL - Capacidad marginal. Solo Tier 1 ($100, 30 días)."
        else:
            return "DENY - Capacidad insuficiente. Balance no puede cubrir parcels consistentemente."

    def generate_report_table(self) -> pd.DataFrame:
        """
        Genera tabla de métricas para reporte.

        Returns:
            DataFrame con métricas CFA formateadas
        """
        results = self.calculate_cfa()

        table_data = {
            'Métrica': [
                'Biweekly Parcel',
                'Total Days Analyzed',
                'Can Pay (Last 90 days)',
                'Can Pay (6 months)',
                'CFA Score (Weighted)',
                'Risk Tier',
                'Avg Balance',
                'Min Balance',
                'Max Consecutive Days',
                'Recommendation'
            ],
            'Valor': [
                f"${results['biweekly_parcel']:.2f}",
                results['total_days'],
                f"{results['pct_90']:.2%}",
                f"{results['pct_6m']:.2%}",
                f"{results['cfa_score']:.2%}",
                results['risk_tier'],
                f"${results['balance_stats']['avg_balance']:.2f}",
                f"${results['balance_stats']['min_balance']:.2f}",
                f"{results['max_consecutive_can_pay_90d']} días",
                results['recommendation']
            ]
        }

        return pd.DataFrame(table_data)

    def plot_temporal_analysis(self, save_path: str = None):
        """
        Genera gráfico temporal de capacidad de pago.

        Args:
            save_path: Ruta para guardar la imagen (opcional)
        """
        fig, axes = plt.subplots(3, 1, figsize=(16, 12))

        # Gráfico 1: Balance diario vs. Biweekly Parcel
        ax1 = axes[0]
        ax1.plot(self.data['date'], self.data['daily_balance'],
                label='Daily Balance', linewidth=1.5, color='#1863DC')
        ax1.axhline(y=self.biweekly_parcel, color='#dc3545', linestyle='--',
                   linewidth=2, label=f'Biweekly Parcel (${self.biweekly_parcel:.2f})')
        ax1.fill_between(self.data['date'], 0, self.biweekly_parcel,
                        alpha=0.1, color='#dc3545', label='Cannot Pay Zone')
        ax1.set_title('Daily Balance vs. Biweekly Parcel Requirement',
                     fontsize=14, fontweight='bold')
        ax1.set_ylabel('Balance ($)', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # Gráfico 2: Can Pay (1/0) a lo largo del tiempo
        ax2 = axes[1]
        colors = ['#dc3545' if x == 0 else '#17CA60' for x in self.data['can_pay']]
        ax2.bar(self.data['date'], self.data['can_pay'], color=colors, width=1, alpha=0.7)
        ax2.set_title('Daily Payment Capacity (Can Pay = 1, Cannot Pay = 0)',
                     fontsize=14, fontweight='bold')
        ax2.set_ylabel('Can Pay', fontsize=12)
        ax2.set_ylim(-0.1, 1.1)
        ax2.grid(True, alpha=0.3, axis='y')

        # Gráfico 3: Rolling 30-day CFA
        ax3 = axes[2]
        rolling_cfa = self.data['can_pay'].rolling(window=30, min_periods=1).mean()
        ax3.plot(self.data['date'], rolling_cfa, linewidth=2, color='#0D1752',
                label='30-day Rolling CFA')

        # Zonas de riesgo
        ax3.axhspan(0.85, 1.0, alpha=0.2, color='#17CA60', label='Tier 3 Zone (85%+)')
        ax3.axhspan(0.70, 0.85, alpha=0.2, color='#1863DC', label='Tier 2 Zone (70-84%)')
        ax3.axhspan(0.55, 0.70, alpha=0.2, color='#FFA500', label='Tier 1 Zone (55-69%)')
        ax3.axhspan(0, 0.55, alpha=0.2, color='#dc3545', label='Deny Zone (<55%)')

        ax3.set_title('30-Day Rolling CFA Score', fontsize=14, fontweight='bold')
        ax3.set_ylabel('CFA Score', fontsize=12)
        ax3.set_xlabel('Date', fontsize=12)
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 1)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Gráfico guardado en: {save_path}")

        plt.close()  # Close figure to free memory

    def export_results(self, output_path: str = 'cfa_results.json'):
        """
        Exporta resultados CFA a archivo JSON.

        Args:
            output_path: Ruta del archivo de salida
        """
        results = self.calculate_cfa()

        # Convertir tipos numpy a tipos nativos de Python para JSON
        def convert_to_native(obj):
            if isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        results_serializable = convert_to_native(results)

        with open(output_path, 'w') as f:
            json.dump(results_serializable, f, indent=2)

        print(f"Resultados exportados a: {output_path}")
        return results


# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

def generate_sample_data(days: int = 180, tier: int = 1) -> pd.DataFrame:
    """
    Genera dataset de ejemplo para testing.

    Args:
        days: Número de días a generar (default: 180 = 6 meses)
        tier: Tier del usuario (1, 2, o 3) para simular diferentes patrones

    Returns:
        DataFrame con transacciones sintéticas
    """
    np.random.seed(42)

    # Parámetros por tier
    tier_params = {
        1: {'base_balance': 300, 'income_freq': 14, 'income_amt': 600, 'daily_expense': 25},
        2: {'base_balance': 500, 'income_freq': 14, 'income_amt': 800, 'daily_expense': 30},
        3: {'base_balance': 800, 'income_freq': 14, 'income_amt': 1000, 'daily_expense': 35}
    }

    params = tier_params.get(tier, tier_params[1])

    start_date = datetime.now() - timedelta(days=days)
    dates = [start_date + timedelta(days=i) for i in range(days)]

    data = []
    current_balance = params['base_balance']

    for i, date in enumerate(dates):
        # Income bi-weekly (cada 14 días)
        daily_income = params['income_amt'] if i % params['income_freq'] == 0 else 0

        # Gastos diarios con variabilidad
        daily_expenses = params['daily_expense'] + np.random.randint(-10, 15)

        # Balance actualizado
        current_balance = current_balance + daily_income - daily_expenses

        # Evitar balance negativo extremo (simulación de overdraft protection)
        if current_balance < -100:
            current_balance = 50  # Simular depósito de emergencia

        data.append({
            'date': date,
            'daily_balance': round(current_balance, 2),
            'daily_income': daily_income,
            'daily_expenses': daily_expenses
        })

    return pd.DataFrame(data)


def get_underwriting_rules() -> Dict:
    """
    Retorna reglas de decisión para underwriting basadas en CFA.

    Returns:
        Dict con umbrales y reglas por tier
    """
    return {
        'tier_3': {
            'cfa_min': 0.70,
            'loan_amount': 200,
            'term_days': 90,
            'biweekly_parcel': 35.80,
            'description': 'Premium - Alta capacidad de pago consistente'
        },
        'tier_2': {
            'cfa_min': 0.60,
            'loan_amount': 150,
            'term_days': 60,
            'biweekly_parcel': 39.72,
            'description': 'Standard - Buena capacidad de pago'
        },
        'tier_1': {
            'cfa_min': 0.50,
            'loan_amount': 100,
            'term_days': 30,
            'biweekly_parcel': 51.98,
            'description': 'Starter - Capacidad marginal de pago'
        },
        'deny': {
            'cfa_max': 0.50,
            'description': 'Balance insuficiente para cubrir parcels consistentemente'
        }
    }


# ============================================
# EJEMPLO DE USO
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("CASH FLOW AFFORDABILITY (CFA) CALCULATOR")
    print("=" * 60)
    print()

    # Generar datos de ejemplo para Tier 2
    print("Generando dataset de ejemplo (180 días, Tier 2)...")
    sample_data = generate_sample_data(days=180, tier=2)

    # Inicializar calculador con biweekly parcel de Tier 2
    biweekly_parcel = 39.72
    calculator = CFACalculator(sample_data, biweekly_parcel)

    # Calcular CFA
    print("Calculando CFA...")
    results = calculator.calculate_cfa()

    # Mostrar tabla de resultados
    print("\n" + "=" * 60)
    print("RESULTADOS CFA")
    print("=" * 60)
    report_table = calculator.generate_report_table()
    print(report_table.to_string(index=False))

    # Mostrar interpretación
    print("\n" + "=" * 60)
    print("INTERPRETACIÓN")
    print("=" * 60)
    print(f"CFA Score: {results['cfa_score']:.2%}")
    print(f"Risk Tier: {results['risk_tier']}")
    print(f"Recommendation: {results['recommendation']}")

    # Mostrar reglas de underwriting
    print("\n" + "=" * 60)
    print("REGLAS DE UNDERWRITING")
    print("=" * 60)
    rules = get_underwriting_rules()
    for tier_name, tier_rules in rules.items():
        print(f"\n{tier_name.upper().replace('_', ' ')}:")
        for key, value in tier_rules.items():
            print(f"  {key}: {value}")

    # Exportar resultados
    print("\nExportando resultados...")
    calculator.export_results('cfa_results.json')

    # Generar gráficos
    print("\nGenerando visualizaciones...")
    calculator.plot_temporal_analysis(save_path='cfa_temporal_analysis.png')

    print("\n✅ Proceso completado!")
