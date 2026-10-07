import { useQuery } from '@tanstack/react-query'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { apiGet, type RunningBot } from '@/lib/api'

export function RunningBotsPage() {
  const { data: bots, isPending, error } = useQuery({
    queryKey: ['bots', 'running'],
    queryFn: () => apiGet<RunningBot[]>('/bots/running'),
    refetchInterval: 10_000, // poll every 10s to keep the list live
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bots actifs</CardTitle>
        <CardDescription>Bots currently running in the BotManager (refreshed every 10s)</CardDescription>
      </CardHeader>
      <CardContent>
        {isPending && <p className="text-muted-foreground">Loading…</p>}
        {error && <p className="text-destructive">Cannot reach the API: {error.message}</p>}
        {bots && bots.length === 0 && <p className="text-muted-foreground">No bot running.</p>}
        {bots && bots.length > 0 && (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Bot ID</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Params</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bots.map((bot) => (
                <TableRow key={bot.bot_id}>
                  <TableCell className="font-mono text-xs">{bot.bot_id}</TableCell>
                  <TableCell>{bot.strategy}</TableCell>
                  <TableCell>
                    <Badge variant={bot.status === 'running' ? 'default' : 'secondary'}>{bot.status}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs whitespace-pre-wrap">
                    {Object.entries(bot.params)
                      .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
                      .join('\n')}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
