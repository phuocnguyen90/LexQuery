// src/app/admin/api/responses/route.ts

import { NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth/auth-options"
import prisma from "@/lib/prisma"

export async function GET(req: Request) {
  const session = await getServerSession(authOptions)

  if (!session || (session.user.role !== "ADMIN" && session.user.role !== "MODERATOR")) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  // Fetch chatbot responses or other admin data
  const responses = await prisma.chatResponse.findMany({
    include: { user: true },
  })

  return NextResponse.json(responses, { status: 200 })
}
