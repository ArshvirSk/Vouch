import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "http://localhost:54321"; // fallback
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "fallback_key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
