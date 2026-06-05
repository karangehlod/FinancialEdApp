import React, { useEffect, useState, useCallback } from 'react'
import { chatService, type ChatConversation } from '@/services/chatService'

interface Props {
  active?: string | null
  onSelect?: (id: string) => void
  onDelete?: (id: string) => void
}

export const ConversationsList: React.FC<Props> = ({ active = null, onSelect, onDelete }) => {
  const [convs, setConvs] = useState<ChatConversation[]>([])
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await chatService.getConversations()
      const items = (res.conversations ?? []).map((c: ChatConversation) => ({
        id: c.id,
        last: c.last,
        ts: c.ts,
      }))
      setConvs(items)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load, active])

  const handleDelete = useCallback(
    async (id: string) => {
      setDeleting(id)
      try {
        await chatService.deleteConversation(id)
        await load()
        if (onSelect && id === active) {
          onSelect('new')
        }
        if (onDelete) onDelete(id)
      } catch {
        // ignore — parent UI shows toasts
      } finally {
        setDeleting(null)
      }
    },
    [load, onSelect, active, onDelete]
  )

  return (
    <div className="w-64 border-r pr-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold">Conversations</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void (onSelect ? onSelect('new') : undefined)}
            className="text-sm text-primary-600"
          >
            New
          </button>
          <button type="button" className="text-sm text-gray-500" onClick={() => void load()}>
            Refresh
          </button>
        </div>
      </div>

      <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-10rem)]">
        {loading && <div className="text-sm text-gray-500">Loading…</div>}
        {!loading && convs.length === 0 && <div className="text-sm text-gray-500">No conversations</div>}
        {convs.map((c) => (
          <div key={c.id} className={`p-2 rounded ${c.id === active ? 'bg-primary-50 dark:bg-primary-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
            <div className="flex items-start justify-between">
              <button type="button" className="text-left flex-1 truncate text-gray-900 dark:text-gray-100" onClick={() => onSelect?.(c.id)}>
                <div className="text-sm font-medium truncate">{c.last ? (c.last.length > 60 ? c.last.slice(0, 60) + '…' : c.last) : 'New conversation'}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {c.ts ? new Date(c.ts).toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' }) : ''}
                </div>
              </button>
              <button type="button" className="text-red-500 text-xs ml-2" onClick={() => void handleDelete(c.id)} disabled={deleting === c.id}>
                {deleting === c.id ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ConversationsList
