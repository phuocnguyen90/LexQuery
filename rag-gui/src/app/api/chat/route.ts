// src/app/api/chat/route.ts

import { NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth/auth-options"
import prisma from "@/lib/prisma"
import { getUsageLimits } from "@/lib/usage"
import { encode } from "gpt-3-encoder"

interface ChatRequest {
  message: string
}

export async function POST(req: Request) {
  const session = await getServerSession(authOptions)
  
  if (!session || !session.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { message }: ChatRequest = await req.json()

  // Fetch user details
  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    include: { subscription: true },
  })

  if (!user) {
    return NextResponse.json({ error: "User not found" }, { status: 404 })
  }

  // Determine usage limits
  const tier = user.subscription?.tier
  const usageLimits = getUsageLimits(user.role, tier)

  // Get today's usage
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  let usage = await prisma.usage.findUnique({
    where: {
      userId_date: {
        userId: user.id,
        date: today,
      },
    },
  })

  if (!usage) {
    // Create a new usage record for today
    usage = await prisma.usage.create({
      data: {
        userId: user.id,
        date: today,
        questionsUsed: 0,
        tokensUsed: 0,
      },
    })
  }

  // Calculate tokens for the message
  const tokens = encode(message).length

  // Check if usage limits are exceeded
  if (usage.questionsUsed + 1 > usageLimits.maxQuestions || usage.tokensUsed + tokens > usageLimits.maxTokens) {
    return NextResponse.json({ error: "Usage limits exceeded. Please upgrade your membership." }, { status: 403 })
  }

  // Update usage
  usage = await prisma.usage.update({
    where: { id: usage.id },
    data: {
      questionsUsed: { increment: 1 },
      tokensUsed: { increment: tokens },
    },
  })

  // Check for template answers
  const template = await prisma.templateAnswer.findUnique({
    where: { question: message },
  })

  let botResponse: string

  if (template) {
    botResponse = template.answer
  } else {
    // Replace this mock response with your RAG pipeline or LLM logic
    botResponse = `You asked: "${message}"`
  }

  // Save the chat response
  await prisma.chatResponse.create({
    data: {
      userId: user.id,
      question: message,
      response: botResponse,
    },
  })

  const encoderStream = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoderStream.encode(botResponse))
      controller.close()
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  })
}
