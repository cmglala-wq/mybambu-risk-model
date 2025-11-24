# Cash Flow Affordability (CFA) - Documentación Técnica

## 📋 Resumen Ejecutivo

La métrica **Cash Flow Affordability (CFA)** mide la capacidad de pago del usuario a nivel diario, basada en su habilidad para cubrir el **biweekly parcel** (pago quincenal) en cualquier día del periodo de análisis.

**Objetivo:** Determinar si el usuario tiene suficiente balance disponible para realizar pagos quincenales de manera consistente, sin importar el día en que se le solicite el pago.

---

## 🔢 Especificaciones Técnicas

### Dataset Requerido
Mínimo **6 meses de transacciones** con las siguientes columnas:
- `date`: Fecha de la transacción
- `daily_balance`: Balance disponible al final del día
- `daily_income`: Ingresos recibidos en el día
- `daily_expenses`: Gastos realizados en el día
- `biweekly_parcel`: Monto del pago quincenal según tier del usuario

### Variables Calculadas
```python
daily_net = daily_income - daily_expenses
can_pay[d] = 1 if daily_balance[d] >= biweekly_parcel else 0
```

---

## 📐 Metodología de Cálculo

### 1. Determinación de Capacidad de Pago Diaria
Para cada día del dataset, se evalúa si el usuario **puede** pagar:

```
can_pay[d] = 1  si  daily_balance[d] >= biweekly_parcel
can_pay[d] = 0  si  daily_balance[d] < biweekly_parcel
```

### 2. Métricas Temporales

#### **pct_90** (Últimos 90 días - 70% peso)
```
pct_90 = sum(can_pay over last 90 days) / 90
```
- Representa el **% de días en los últimos 3 meses** en que el usuario podría pagar
- Mayor peso porque refleja el comportamiento reciente

#### **pct_6m** (Últimos 6 meses - 30% peso)
```
pct_6m = sum(can_pay over last 6 months) / total_days_6m
```
- Representa el **% de días en todo el periodo** en que el usuario podría pagar
- Menor peso pero importante para detectar estacionalidad

### 3. Score CFA Final (Ponderado)
```
CFA = (pct_90 × 0.70) + (pct_6m × 0.30)
```

**Rango:** 0.0 a 1.0 (0% a 100%)

---

## 🎯 Interpretación del CFA Score

| CFA Score | Interpretación | Capacidad de Pago |
|-----------|----------------|-------------------|
| **85-100%** | 🟢 **Excelente** | Usuario puede pagar 85+ días de cada 100 días |
| **70-84%** | 🟡 **Buena** | Usuario puede pagar 70-84 días de cada 100 días |
| **55-69%** | 🟠 **Marginal** | Usuario puede pagar 55-69 días de cada 100 días |
| **<55%** | 🔴 **Insuficiente** | Usuario puede pagar menos de 55 días de cada 100 días |

---

## 📊 Reglas de Decisión para Underwriting

### Tier 3: Premium (CFA ≥ 85%)
```
Loan Amount: $200
Term: 90 días
APR: 30%
Biweekly Parcel: $35.80 (6 pagos)
Default Rate: ~5%

Criterios:
✓ CFA Score ≥ 85%
✓ Balance promedio > $800
✓ Max consecutive can_pay ≥ 60 días
✓ Variabilidad de balance moderada (std < $1500)

Decisión: APPROVE - Alta capacidad de pago consistente
```

### Tier 2: Standard (CFA 70-84%)
```
Loan Amount: $150
Term: 60 días
APR: 36%
Biweekly Parcel: $39.72 (4 pagos)
Default Rate: ~9%

Criterios:
✓ CFA Score 70-84%
✓ Balance promedio > $500
✓ Max consecutive can_pay ≥ 40 días
✓ Positive days (daily_net > 0) ≥ 15%

Decisión: APPROVE - Buena capacidad de pago
```

### Tier 1: Starter (CFA 55-69%)
```
Loan Amount: $100
Term: 30 días
APR: 48%
Biweekly Parcel: $51.98 (2 pagos)
Default Rate: ~14%

Criterios:
✓ CFA Score 55-69%
✓ Balance promedio > $300
✓ Max consecutive can_pay ≥ 20 días
✓ Min balance > $100 (evitar balance negativo extremo)

Decisión: CONDITIONAL APPROVE - Capacidad marginal, monitorear de cerca
```

### Denied (CFA < 55%)
```
Criterios:
✗ CFA Score < 55%
✗ Balance insuficiente para cubrir parcels consistentemente
✗ Alta variabilidad de balance sin pattern estable

Decisión: DENY - Riesgo inaceptable. Recomendar esperar 3-6 meses.
```

---

## 🔍 Análisis Complementarios

### 1. **Max Consecutive Days**
- Secuencia máxima de días consecutivos con `can_pay = 1`
- Indica estabilidad y previsibilidad del flujo de caja
- **Tier 3:** Requiere ≥60 días consecutivos
- **Tier 2:** Requiere ≥40 días consecutivos
- **Tier 1:** Requiere ≥20 días consecutivos

### 2. **Balance Statistics**
```python
avg_balance: Promedio de balance diario
min_balance: Balance mínimo (detecta riesgo de overdraft)
max_balance: Balance máximo (indica capacidad máxima)
std_balance: Desviación estándar (mide volatilidad)
```

**Interpretación:**
- **Std alto + CFA bajo** = Flujo errático, alto riesgo
- **Std bajo + CFA alto** = Flujo estable, bajo riesgo
- **Min balance negativo** = Flag de riesgo (overdrafts recurrentes)

### 3. **Daily Net Flow**
```python
avg_daily_net: Promedio de (income - expenses) diario
positive_days_pct: % de días con daily_net > 0
```

**Interpretación:**
- **positive_days_pct < 10%** = Ingresos muy esporádicos (quincenal/mensual)
- **avg_daily_net positivo** = Usuario está ahorrando
- **avg_daily_net negativo** = Usuario está quemando balance

---

## ⚠️ Factores de Riesgo (Red Flags)

### 🚨 Alto Riesgo
1. **CFA < 40%** - Balance casi nunca cubre el parcel
2. **Min balance < 0** - Overdrafts recurrentes
3. **Max consecutive days < 10** - No hay estabilidad
4. **Positive days < 5%** - Ingresos muy infrecuentes
5. **Std balance > 2× avg balance** - Extrema volatilidad

### ⚠️ Riesgo Moderado
1. **CFA 40-55%** - Border line
2. **Min balance < $50** - Balance muy ajustado
3. **Max consecutive days 10-20** - Estabilidad marginal
4. **Positive days 5-10%** - Ingresos poco frecuentes

---

## 📈 Casos de Uso

### Ejemplo 1: Usuario Tier 3 (Aprobado)
```json
{
  "cfa_score": 0.92,
  "pct_90": 0.94,
  "pct_6m": 0.88,
  "avg_balance": 3200,
  "min_balance": 800,
  "max_consecutive_can_pay_90d": 78,
  "recommendation": "APPROVE - Tier 3 ($200)"
}
```
**Interpretación:** Usuario tiene balance consistentemente alto, puede pagar 92% de los días. Bajo riesgo.

### Ejemplo 2: Usuario Tier 1 (Condicional)
```json
{
  "cfa_score": 0.62,
  "pct_90": 0.67,
  "pct_6m": 0.53,
  "avg_balance": 420,
  "min_balance": 120,
  "max_consecutive_can_pay_90d": 28,
  "recommendation": "CONDITIONAL - Tier 1 ($100)"
}
```
**Interpretación:** Usuario tiene balance suficiente 62% del tiempo. Solo para préstamo pequeño con monitoreo.

### Ejemplo 3: Usuario Denied
```json
{
  "cfa_score": 0.38,
  "pct_90": 0.41,
  "pct_6m": 0.32,
  "avg_balance": 180,
  "min_balance": -50,
  "max_consecutive_can_pay_90d": 8,
  "recommendation": "DENY - Balance insuficiente"
}
```
**Interpretación:** Usuario solo puede pagar 38% de los días, balance muy bajo, riesgo alto.

---

## 🛠️ Implementación en Producción

### 1. Pipeline de Datos
```python
from cfa_calculator import CFACalculator

# 1. Extraer 6 meses de transacciones de Snowflake
df = snowflake.execute("""
    SELECT date, daily_balance, daily_income, daily_expenses
    FROM user_transactions
    WHERE user_id = ?
    AND date >= DATEADD(month, -6, CURRENT_DATE())
    ORDER BY date
""", user_id)

# 2. Calcular CFA
biweekly_parcel = get_parcel_for_tier(user_tier)
calculator = CFACalculator(df, biweekly_parcel)
results = calculator.calculate_cfa()

# 3. Aplicar regla de decisión
if results['cfa_score'] >= 0.85:
    approve_tier_3(user_id)
elif results['cfa_score'] >= 0.70:
    approve_tier_2(user_id)
elif results['cfa_score'] >= 0.55:
    approve_tier_1(user_id)
else:
    deny_application(user_id, reason="CFA insuficiente")
```

### 2. Monitoreo Continuo
- **Recalcular CFA mensualmente** para todos los usuarios activos
- **Alert si CFA baja >10%** en un mes
- **Auto-downgrade** si CFA cae debajo del umbral de su tier actual
- **Graduation path:** Si CFA mejora >15% por 3 meses consecutivos, ofrecer upgrade

---

## 📚 Referencias y Fórmulas

### Biweekly Parcels por Tier
```
Tier 1: $51.98 (loan $100, APR 48%, 30 días, 2 parcels)
Tier 2: $39.72 (loan $150, APR 36%, 60 días, 4 parcels)
Tier 3: $35.80 (loan $200, APR 30%, 90 días, 6 parcels)
```

### Ponderación Temporal
- **70% últimos 90 días:** Comportamiento reciente es el mejor predictor
- **30% últimos 6 meses:** Captura estacionalidad y tendencias de largo plazo

### Umbrales de Decisión
Basados en análisis de default rates históricos:
- **85% CFA** → 5% default (Tier 3)
- **70% CFA** → 9% default (Tier 2)
- **55% CFA** → 14% default (Tier 1)
- **<55% CFA** → >20% default (Denied)

---

## ✅ Ventajas de la Métrica CFA

1. ✅ **Simple y explicable** - Fácil de entender para underwriters
2. ✅ **Forward-looking** - Proyecta capacidad de pago futura
3. ✅ **Resistente a gaming** - No puede ser manipulada fácilmente
4. ✅ **Sensible al timing** - Penaliza balance bajo justo antes de pago
5. ✅ **Captura estacionalidad** - El componente 6m detecta patterns irregulares

---

## 🔧 Archivo de Uso

```bash
# 1. Instalar dependencias
pip install pandas numpy matplotlib seaborn

# 2. Ejecutar calculador
python3 cfa_calculator.py

# 3. Outputs generados
# - cfa_results.json: Métricas detalladas
# - cfa_temporal_analysis.png: Visualización completa
```

---

## 📞 Contacto y Soporte

Para preguntas sobre la implementación de CFA:
- **Repositorio:** https://github.com/cmglala-wq/mybambu-risk-model
- **Documentación:** /CFA_DOCUMENTATION.md
- **Script:** /cfa_calculator.py

---

**Última actualización:** 2025-11-24
**Versión:** 1.0
**Autor:** MyBambu Risk Team
