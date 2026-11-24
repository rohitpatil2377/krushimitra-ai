import { getJson, patchJson, postJson } from '@/services/api';

// Phone-OTP auth against the FastAPI backend.
//
// The OTP is NOT really sent yet — no SMS provider is wired — and the backend says so in its
// response (`otp_is_real: false`). The login screen surfaces that instead of a fake
// "check your SMS", because a farmer who waits for a message that never arrives concludes the
// app is broken, which is worse than telling them the truth.

export interface Farmer {
  id: number;
  phone: string;
  name?: string;
  village?: string;
  district?: string;
  preferredLang: string;
}

export interface OtpRequestResult {
  sent: boolean;
  otpIsReal: boolean;
  devOtp?: string;
  messageMr?: string;
}

interface FarmerResponse {
  id: number;
  phone: string;
  name?: string | null;
  village?: string | null;
  district?: string | null;
  preferred_lang?: string;
}

function toFarmer(d: FarmerResponse): Farmer {
  return {
    id: d.id,
    phone: d.phone,
    name: d.name ?? undefined,
    village: d.village ?? undefined,
    district: d.district ?? undefined,
    preferredLang: d.preferred_lang ?? 'mr',
  };
}

export async function requestOtp(phone: string): Promise<OtpRequestResult> {
  const d = await postJson<{
    sent: boolean;
    otp_is_real: boolean;
    dev_otp?: string;
    message_mr?: string;
  }>('/auth/otp/request', { phone });
  return {
    sent: d.sent,
    otpIsReal: d.otp_is_real,
    devOtp: d.dev_otp,
    messageMr: d.message_mr,
  };
}

export async function verifyOtp(phone: string, otp: string): Promise<string> {
  const d = await postJson<{ access_token: string }>('/auth/otp/verify', { phone, otp });
  return d.access_token;
}

export async function fetchMe(): Promise<Farmer> {
  return toFarmer(await getJson<FarmerResponse>('/auth/me'));
}

export async function updateMe(patch: {
  name?: string;
  village?: string;
  district?: string;
  preferredLang?: string;
  deviceId?: string;
}): Promise<Farmer> {
  return toFarmer(
    await patchJson<FarmerResponse>('/auth/me', {
      name: patch.name,
      village: patch.village,
      district: patch.district,
      preferred_lang: patch.preferredLang,
      device_id: patch.deviceId,
    }),
  );
}
