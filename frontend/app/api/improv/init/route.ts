import { NextResponse } from 'next/server';
import { AccessToken } from 'livekit-server-sdk';

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

export async function POST(req: Request) {
  try {
    if (!API_KEY || !API_SECRET || !LIVEKIT_URL) {
      throw new Error('LiveKit environment variables not set');
    }

    const { name } = await req.json();
    if (!name) {
      return new NextResponse('Name is required', { status: 400 });
    }

    const at = new AccessToken(API_KEY, API_SECRET, {
      identity: `player-${Date.now()}`,
      ttl: '15m',
    });

    at.metadata = JSON.stringify({ playerName: name });

    at.addGrant({
      room: 'improv-battle',
      roomJoin: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
    });

    const token = await at.toJwt();

    return NextResponse.json({ serverUrl: LIVEKIT_URL, token });
  } catch (error) {
    console.error(error);
    return new NextResponse('Internal server error', { status: 500 });
  }
}
