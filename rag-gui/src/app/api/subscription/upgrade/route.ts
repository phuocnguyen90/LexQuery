// src/app/api/subscription/upgrade/route.ts

import { NextResponse } from "next/server"
import { getServerSession } from "next-auth/next"
import { authOptions } from "@/lib/auth/auth-options"
import prisma from "@/lib/prisma"

interface UpgradeRequest {
  tier: string
}

export async function POST(req: Request) {
  const session = await getServerSession(authOptions)

  if (!session || !session.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { tier }: UpgradeRequest = await req.json()

  // Validate tier
  const validTiers = ["UNLIMITED", "PAY_AS_YOU_GO", "PREPAID_BASIC", "PREPAID_PRO", "PREPAID_ENTERPRISE"]
  if (!validTiers.includes(tier)) {
    return NextResponse.json({ error: "Invalid subscription tier." }, { status: 400 })
  }

  try {
    // Update or create subscription
    const subscription = await prisma.subscription.upsert({
      where: { userId: session.user.id },
      update: { tier },
      create: { tier, userId: session.user.id },
    })

    return NextResponse.json({ message: "Subscription updated successfully." }, { status: 200 })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: "Failed to update subscription." }, { status: 500 })
  }
}
