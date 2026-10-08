// Mirrors BotStatus in backend/app/bots/base.py
export type BotStatus = 'created' | 'running' | 'paused' | 'stopped'

// Mirrors RunningBot in backend/app/api/queries/bots.py
export type RunningBot = {
  bot_id: string
  status: BotStatus
  strategy: string
  params: Record<string, unknown>
}
