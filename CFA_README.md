# Cash Flow Affordability (CFA) - Quick Start Guide

## 🚀 Archivos Generados

```
├── cfa_calculator.py              # Script principal de cálculo CFA
├── CFA_DOCUMENTATION.md           # Documentación técnica completa
├── cfa_results.json               # Resultados de ejemplo (JSON)
└── cfa_temporal_analysis.png      # Visualización temporal (3 gráficos)
```

## 📊 Output de Ejemplo

### Métricas CFA
```
Biweekly Parcel:      $39.72
Total Days Analyzed:  180
Can Pay (90 days):    100.00%
Can Pay (6 months):   100.00%
CFA Score:            100.00%
Risk Tier:            Tier 3 (Premium) - CFA 85-100%
Avg Balance:          $3,144.11
Recommendation:       APPROVE - Alta capacidad de pago
```

### Visualizaciones Generadas

El gráfico `cfa_temporal_analysis.png` contiene 3 paneles:

1. **Panel 1: Balance Diario vs. Biweekly Parcel**
   - Línea azul: Balance diario del usuario
   - Línea roja punteada: Umbral de biweekly parcel
   - Zona roja: Días donde NO puede pagar

2. **Panel 2: Capacidad de Pago Diaria (Can Pay)**
   - Barras verdes: Días donde SÍ puede pagar (can_pay = 1)
   - Barras rojas: Días donde NO puede pagar (can_pay = 0)

3. **Panel 3: Rolling 30-Day CFA Score**
   - Línea azul: CFA score móvil de 30 días
   - Zonas de color: Tier 3 (verde), Tier 2 (azul), Tier 1 (naranja), Deny (rojo)

## 🎯 Uso Básico

### Con Datos Reales (Snowflake)
```python
from cfa_calculator import CFACalculator
import pandas as pd

# 1. Cargar datos de Snowflake
df = pd.read_sql("""
    SELECT date, daily_balance, daily_income, daily_expenses
    FROM user_transactions
    WHERE user_id = 'USER123'
    AND date >= DATEADD(month, -6, CURRENT_DATE())
""", snowflake_conn)

# 2. Calcular CFA
biweekly_parcel = 39.72  # Tier 2
calculator = CFACalculator(df, biweekly_parcel)

# 3. Obtener resultados
results = calculator.calculate_cfa()
print(f"CFA Score: {results['cfa_score']:.2%}")
print(f"Recommendation: {results['recommendation']}")

# 4. Generar visualización
calculator.plot_temporal_analysis(save_path='user_cfa_analysis.png')

# 5. Exportar resultados
calculator.export_results('user_cfa_results.json')
```

### Con Datos de Ejemplo
```python
from cfa_calculator import generate_sample_data, CFACalculator

# Generar datos sintéticos
data = generate_sample_data(days=180, tier=2)

# Calcular CFA
calculator = CFACalculator(data, biweekly_parcel=39.72)
results = calculator.calculate_cfa()

# Ver tabla de resultados
print(calculator.generate_report_table())
```

## 🔍 Reglas de Decisión

| CFA Score | Tier | Loan Amount | Biweekly Parcel | Decision |
|-----------|------|-------------|-----------------|----------|
| ≥85% | Tier 3 | $200 | $35.80 | **APPROVE** |
| 70-84% | Tier 2 | $150 | $39.72 | **APPROVE** |
| 55-69% | Tier 1 | $100 | $51.98 | **CONDITIONAL** |
| <55% | - | - | - | **DENY** |

## 📐 Fórmula CFA

```
1. can_pay[d] = 1 if daily_balance[d] >= biweekly_parcel else 0

2. pct_90 = sum(can_pay over last 90 days) / 90

3. pct_6m = sum(can_pay over last 6 months) / total_days

4. CFA = (pct_90 × 0.70) + (pct_6m × 0.30)
```

## ⚠️ Consideraciones Importantes

1. **Dataset mínimo:** 90 días (preferible 180 días)
2. **Biweekly parcel:** Debe corresponder al tier del usuario
3. **Balance diario:** Debe ser el balance al final del día
4. **Recalcular mensualmente:** Para monitoreo continuo

## 📚 Documentación Completa

Ver `CFA_DOCUMENTATION.md` para:
- Metodología detallada
- Casos de uso
- Interpretación de resultados
- Factores de riesgo (red flags)
- Pipeline de producción

## 🛠️ Instalación

```bash
pip install pandas numpy matplotlib seaborn
python3 cfa_calculator.py  # Ejecutar ejemplo
```

## 📧 Soporte

- Documentación: `CFA_DOCUMENTATION.md`
- Script: `cfa_calculator.py`
- Repositorio: https://github.com/cmglala-wq/mybambu-risk-model
