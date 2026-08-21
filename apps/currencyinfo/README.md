# Currency Info
MIT License

Real-time crypto trade stream from Binance WebSocket into Frappe.

## Features
- Live BTC/USDT trade feed (`wss://stream.binance.com:9443/ws/btcusdt@trade`)
- Desk page with live price, side, and recent trades
- Settings for stream URL / symbol
- Optional background streamer that publishes Frappe realtime events

## Setup
```bash
bench get-app /path/to/currencyinfo   # or place under apps/
bench --site site1.local install-app currencyinfo
bench build --app currencyinfo
```

Open **Currency Info** workspace or page **Currency Info Live**.
