// src/app/api/reset-usage/route.ts

import { NextResponse } from "next/server"
import prisma from "@/lib/prisma"

export async function POST(req: Request) {
  try {
    // Reset all users' usage for the day by creating a new record or setting to 0
    // This example assumes that Usage records are created on-demand
    // If you have a separate reset mechanism, adjust accordingly

    // Alternatively, you can delete all Usage records older than today if they are meant to be per-day
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    // Optional: Clean up Usage records older than today
    await prisma.usage.deleteMany({
      where: {
        date: {
          lt: today,
        },
      },
    })

    return NextResponse.json({ message: "Usage reset successfully" }, { status: 200 })
  } catch (error) {
    console.error(error)
    return NextResponse.json({ error: "Failed to reset usage" }, { status: 500 })
  }
}
