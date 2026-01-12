/** Lightweight password strength estimate (0-4) for the signup meter. */
export function passwordStrength(pw: string): {
  score: number;
  label: string;
} {
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  score = Math.min(score, 4);
  const label = ["Very weak", "Weak", "Fair", "Good", "Strong"][score];
  return { score, label };
}
