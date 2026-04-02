import apiClient from './client'

export interface ChatRequest {
  session_id: string
  message: string
}

export interface ChatResponse {
  response: string
  session_id: string
  latency_ms: number
  fallback_used: boolean
}

const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY as string | undefined
const GEMINI_URL =
  'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent'

// Call Gemini directly from the browser when backend is unavailable
async function callGeminiDirect(message: string): Promise<ChatResponse> {
  if (!GEMINI_API_KEY) throw new Error('No Gemini API key configured')

  const start = Date.now()
  const prompt = `You are an AI assistant for a Smart Supply Chain Optimization platform.
You help logistics managers understand shipment risks, disruptions, and routing decisions.
Answer concisely and professionally.

User: ${message}`

  const res = await fetch(`${GEMINI_URL}?key=${GEMINI_API_KEY}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { maxOutputTokens: 512, temperature: 0.7 },
    }),
  })

  if (!res.ok) {
    const err = await res.text()
    throw new Error(`Gemini API error ${res.status}: ${err}`)
  }

  const data = await res.json()
  const text: string = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? 'No response from AI.'

  return {
    response: text,
    session_id: '',
    latency_ms: Date.now() - start,
    fallback_used: false,
  }
}

export const sendChatMessage = async (data: ChatRequest): Promise<ChatResponse> => {
  // Try backend first; fall back to direct Gemini call
  try {
    const res = await apiClient.post<ChatResponse>('/api/v1/ai/chat', data)
    return res.data
  } catch {
    if (GEMINI_API_KEY) {
      return callGeminiDirect(data.message)
    }
    throw new Error('AI service unavailable and no Gemini API key configured.')
  }
}

export const generateNarrativeReport = async (params: {
  start_date: string
  end_date: string
}): Promise<{ report: string; generated_at: string }> => {
  // Try backend first; fall back to direct Gemini call
  try {
    const res = await apiClient.post('/api/v1/ai/reports/narrative', params)
    return res.data
  } catch {
    if (GEMINI_API_KEY) {
      const response = await callGeminiDirect(
        `Generate a supply chain performance narrative report for the period ${params.start_date} to ${params.end_date}. Include sections on: overall performance, key disruptions, risk trends, and recommendations.`
      )
      return { report: response.response, generated_at: new Date().toISOString() }
    }
    throw new Error('AI service unavailable.')
  }
}
