// src/app/admin/api/chat-responses/route.ts

import { NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth/auth-options"
import prisma from "@/lib/prisma"

export async function GET(req: Request) {
  const session = await getServerSession(authOptions)

  if (!session || (session.user.role !== "ADMIN" && session.user.role !== "MODERATOR")) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const responses = await prisma.chatResponse.findMany({
    include: { user: true },
    orderBy: { createdAt: "desc" },
  })

  return NextResponse.json(responses, { status: 200 })
}

export async function POST(req: Request) {
  const session = await getServerSession(authOptions)

  if (!session || session.user.role !== "ADMIN") {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { question, answer } = await req.json()

  if (!question || !answer) {
    return NextResponse.json({ error: "Question and answer are required" }, { status: 400 })
  }

  try {
    const template = await prisma.templateAnswer.create({
      data: {
        question,
        answer,
      },
    })

    return NextResponse.json(template, { status: 201 })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: "Failed to create template answer" }, { status: 500 })
  }
}
