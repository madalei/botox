// Mirrors Order in backend/app/models/order.py
export type Order = {
  id: string
  bot_id: string
  symbol: string
  side: string
  price: number
  amount: number
  status: string
  stop_loss: number | null
  take_profit: number | null
  created_at: string
  executed_at: string | null
}
