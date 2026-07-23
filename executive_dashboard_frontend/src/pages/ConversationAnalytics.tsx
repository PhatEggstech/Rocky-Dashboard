import { useState, useEffect, useRef } from 'react'
import { Send, Bot, User, RefreshCw, MessageSquare, AlertCircle } from 'lucide-react'
import { Card, CardHeader } from '@/components/ui/card'
import { sendChatMessage, fetchChatConfig } from '@/lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const SUGGESTIONS = [
  "Doanh thu Rocky HCM tháng này?",
  "Sản phẩm nào bán chạy nhất?",
  "Ai là nhân viên bán hàng tốt nhất?",
  "Giải thích công nợ đại lý là gì?",
]

export function ConversationAnalytics() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Xin chào! Tôi là Trợ lý AI của Rocky Lens Dashboard. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về doanh số, tồn kho, đơn hàng, khách hàng, nhân viên hoặc công nợ.'
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [config, setConfig] = useState<{ provider: string; model: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    // Fetch AI config
    fetchChatConfig()
      .then(res => {
        if (res.ok) {
          setConfig({ provider: res.provider, model: res.model })
        }
      })
      .catch(err => {
        console.error("Failed to fetch chat config:", err)
      })
  }, [])

  useEffect(() => {
    // Scroll to bottom on new messages
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return

    setError(null)
    const userMsg: Message = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      // Send message along with history (excluding the first welcome message to keep it clean)
      const historyToSend = messages.slice(1).map(m => ({ role: m.role, content: m.content }))
      const res = await sendChatMessage(text, historyToSend)
      
      if (res.ok && res.response) {
        setMessages(prev => [...prev, { role: 'assistant', content: res.response || '' }])
      } else {
        setError(res.error || 'Có lỗi xảy ra khi gọi AI Assistant.')
      }
    } catch (err) {
      console.error(err)
      setError('Không thể kết nối đến máy chủ AI.')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setMessages([
      {
        role: 'assistant',
        content: 'Tôi đã xóa lịch sử trò chuyện. Bạn muốn tra cứu thông tin gì tiếp theo?'
      }
    ])
    setError(null)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] max-h-[850px] space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">AI Assistant</h1>
          <p className="text-sm text-slate-500 mt-1">Trò chuyện với AI để tra cứu thông tin vận hành & báo cáo</p>
        </div>
        {config && (
          <div className="flex items-center gap-2 px-3 py-1 bg-purple-50 border border-purple-100 rounded-full text-xs text-purple-700 font-medium">
            <Bot size={14} className="animate-pulse" />
            <span>{config.model} ({config.provider})</span>
          </div>
        )}
      </div>

      {/* Main Chat Interface */}
      <Card className="flex-1 flex flex-col overflow-hidden border-slate-200 shadow-md rounded-2xl bg-white">
        {/* Chat Title bar */}
        <CardHeader className="py-3 px-4 border-b border-slate-100 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2">
            <MessageSquare size={18} className="text-blue-600" />
            <span className="text-sm font-semibold text-slate-700">Trợ lý Rocky</span>
          </div>
          <button
            onClick={handleClear}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
            title="Xóa cuộc hội thoại"
          >
            <RefreshCw size={12} />
            <span>Xóa lịch sử</span>
          </button>
        </CardHeader>

        {/* Messages list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 bg-slate-50/50">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3 max-w-[85%] ${m.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
            >
              <div className={`p-2 rounded-xl flex-shrink-0 ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-purple-100 text-purple-700'}`}>
                {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div
                className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm whitespace-pre-line ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-none'
                    : 'bg-white text-slate-800 border border-slate-100 rounded-tl-none'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-start gap-3 max-w-[85%]">
              <div className="p-2 rounded-xl bg-purple-100 text-purple-700 flex-shrink-0">
                <Bot size={16} />
              </div>
              <div className="px-4 py-3 rounded-2xl bg-white border border-slate-100 rounded-tl-none shadow-sm text-sm text-slate-500 flex items-center gap-2">
                <span className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
                <span>AI đang tìm câu trả lời...</span>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 p-3 bg-rose-50 border border-rose-100 text-rose-700 rounded-xl text-sm max-w-md mx-auto">
              <AlertCircle size={16} className="flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {messages.length === 1 && !loading && (
          <div className="px-4 py-3 bg-slate-50/20 border-t border-slate-100">
            <p className="text-xs font-semibold text-slate-500 mb-2">Gợi ý câu hỏi:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(s)}
                  className="px-3 py-1.5 text-xs text-slate-600 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 rounded-full shadow-sm transition-all"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input box */}
        <div className="p-3 border-t border-slate-100 bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend(input)
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Nhập câu hỏi của bạn ở đây... (ví dụ: Doanh số hôm qua?)"
              className="flex-1 px-4 py-2.5 text-sm bg-slate-50 border border-slate-200 focus:border-blue-400 rounded-xl focus:outline-none focus:bg-white transition-all text-slate-800"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className={`p-2.5 rounded-xl text-white shadow transition-all ${
                !input.trim() || loading
                  ? 'bg-slate-300 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 hover:scale-105 active:scale-95'
              }`}
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </Card>
    </div>
  )
}
