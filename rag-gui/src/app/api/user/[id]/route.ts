// src/app/api/user/[id]/route.ts

import { NextResponse } from "next/server"
import prisma from "@/lib/prisma"

export async function GET(req: Request, { params }: { params: { id: string } }) {
  const { id } = params

  const user = await prisma.user.findUnique({
    where: { id },
    include: { subscription: true, usages: { where: { date: { gte: new Date(new Date().setHours(0, 0, 0, 0)) } }, take: 1 } },
  })

  if (!user) {
    return NextResponse.json({ error: "User not found" }, { status: 404 })
  }

  const todayUsage = user.usages[0] || { questionsUsed: 0, tokensUsed: 0 }

  return NextResponse.json({
    subscription: user.subscription,
    usage: todayUsage,
  }, { status: 200 })
}
