export type AvatarKey = `${number}`;

export type AvatarAsset = {
  key: AvatarKey;
  label: string;
  path: string;
};

export const DEFAULT_AVATAR_KEY: AvatarKey = "1";

export const AVATAR_OPTIONS: AvatarAsset[] = Array.from({ length: 24 }, (_, index) => {
  const key = String(index + 1) as AvatarKey;
  return {
    key,
    label: `Avatar ${key}`,
    path: `/avatars/${key}.png`,
  };
});

export function normaliseAvatarKey(value: string | null | undefined): AvatarKey | null {
  const trimmed = (value || "").trim();
  if (!trimmed) return null;

  const numeric = Number(trimmed);
  if (!Number.isInteger(numeric) || numeric < 1 || numeric > 24) {
    return null;
  }

  return String(numeric) as AvatarKey;
}

export function getAvatarAsset(value: string | null | undefined): AvatarAsset {
  const key = normaliseAvatarKey(value) ?? DEFAULT_AVATAR_KEY;
  return (
    AVATAR_OPTIONS.find((avatar) => avatar.key === key) ??
    AVATAR_OPTIONS.find((avatar) => avatar.key === DEFAULT_AVATAR_KEY) ??
    AVATAR_OPTIONS[0]
  );
}

export function getAvatarPath(value: string | null | undefined): string {
  return getAvatarAsset(value).path;
}

