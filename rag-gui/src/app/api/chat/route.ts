import { NextResponse } from "next/server"

// Mock chat response. Replace with your RAG pipeline logic.
export async function POST(req: Request) {
  const { message } = await req.json()

  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      // Simulate streaming response
      const botResponse = `You said: ${message}`
      controller.enqueue(encoder.encode(botResponse))
      controller.close()
    }
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  })
}
