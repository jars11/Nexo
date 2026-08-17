# Nexo Trading Bot

Bot de trading automatizado para la API de **Nexo Pro**. Monitorea precios en tiempo real, gestiona múltiples perfiles de trading y ejecuta órdenes de compra/venta de forma automática según reglas de ganancia y tolerancia a la fluctuación.

## Características

- Conexión autenticada a la API de Nexo Pro (HMAC-SHA256)
- Soporte para **múltiples perfiles** de trading
- Gestión automática de pares (ej. BTC/USDT)
- Lógica de decisión basada en:
  - Precio máximo alcanzado (`max_sell_value`)
  - Tolerancia a la fluctuación (`fluctuation_tolerance`)
  - Ganancia mínima deseada (fija en USD o en porcentaje)
- Actualización automática del estado de los perfiles en un archivo de texto

## Cómo funciona

1. El bot carga los perfiles desde el archivo `Profiles Nexo Pro.txt`.
2. Consulta periódicamente el precio actual del par.
3. Actualiza el precio máximo alcanzado si corresponde.
4. Evalúa si se cumplen **ambas** condiciones:
   - Se superó la tolerancia de fluctuación desde el máximo.
   - Se alcanzó la ganancia base configurada.
5. Si se cumplen, ejecuta una orden de mercado y actualiza:
   - Saldos (coin / stablecoin)
   - Próximo movimiento (`buy` ↔ `sell`)
   - Archivo de perfiles

## Estructura de un perfil

Ejemplo del archivo `Profiles Nexo Pro.txt`:

```text
Profile 1: Agustin
Stablecoin: USDT
Coins: BTC
Next movement: sell
Amount coins: 0.00053181
Amount stablecoin: 1.8232051796699977
Add stablecoin: 0.0
Last buy value: 114682.0
Max sell value: 113681.46144
Fluctuation tolerance: 0.35%
Base profit per move: 0.0%
