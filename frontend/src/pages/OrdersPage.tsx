import { useQuery } from '@tanstack/react-query'
import { Badge } from '@/components/ui/badge'
import { apiGet } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Order } from '@/types/order'



export function OrdersPage() {
  const { data: orders, isPending, error } = useQuery({
    queryKey: ['orders'],
    queryFn: () => apiGet<Order[]>('/orders'),
    refetchInterval: 30_000, // poll every 30s to keep the list live
  })

    return (
        <Card>
            <CardHeader>
                <CardTitle>Orders</CardTitle>
                <CardDescription>Orders currently in the system (refreshed every 30s)</CardDescription>
            </CardHeader>
            <CardContent>
                {isPending && <p className="text-muted-foreground">Loading…</p>}
                {error && <p className="text-destructive">Cannot reach the API: {error.message}</p>}
                {orders && orders.length === 0 && <p className="text-muted-foreground">No orders.</p>}
                {orders && orders.length > 0 && (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Order ID</TableHead>
                                <TableHead>Symbol</TableHead>
                                <TableHead>Side</TableHead>
                                <TableHead>Price</TableHead>
                                <TableHead>Quantity</TableHead>
                                <TableHead>Status</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {orders.map((order) => (
                                <TableRow key={order.id}>
                                    <TableCell className="font-mono text-xs">{order.id}</TableCell>
                                    <TableCell>{order.symbol}</TableCell>
                                    <TableCell>{order.side}</TableCell>
                                    <TableCell>{order.price}</TableCell>
                                    <TableCell>{order.amount}</TableCell>
                                    <TableCell>
                                        <Badge variant={order.status === 'EXECUTED' ? 'default' : 'secondary'}>{order.status}</Badge>
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


