import { RunningBotsPage } from '@/pages/RunningBotsPage'
import { OrdersPage } from '@/pages/OrdersPage'

function App() {
  return (
    <div className="min-h-screen bg-muted/40">
      <header className="border-b bg-background">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <h1 className="text-xl font-semibold">Botox · Backoffice</h1>
        </div>
      </header>
      <main className="mx-auto max-w-6xl p-6 space-y-6">
        <RunningBotsPage />
        <OrdersPage />
      </main>
    </div>
  )
}

export default App
