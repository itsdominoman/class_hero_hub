export type ProtectedUpdatePhotoDownload = (path: string, options: RequestInit) => Promise<Blob>;

type ObjectUrlApi = {
  createObjectURL(blob: Blob): string;
  revokeObjectURL(url: string): void;
};

export class ProtectedUpdatePhotoClearedError extends Error {
  constructor() {
    super('Protected photo load was cleared.');
    this.name = 'ProtectedUpdatePhotoClearedError';
  }
}

export type ProtectedUpdatePhotoVariant = 'thumbnail' | 'full';

export function protectedUpdatePhotoKey(
  postId: number,
  photoId: number,
  variant: ProtectedUpdatePhotoVariant
): string {
  return `${postId}:${photoId}:${variant}`;
}

export function protectedUpdatePhotoPath(
  postId: number,
  photoId: number,
  variant: ProtectedUpdatePhotoVariant
): string {
  return variant === 'thumbnail'
    ? `/api/teach/updates/${postId}/photos/${photoId}/thumbnail`
    : `/api/teach/updates/${postId}/photos/${photoId}/view`;
}

export class ProtectedUpdatePhotoCache {
  private readonly objectUrls = new Map<string, string>();
  private readonly inFlight = new Map<string, Promise<string>>();
  private readonly objectUrlApi: ObjectUrlApi;
  private generation = 0;

  constructor(objectUrlApi: ObjectUrlApi = URL) {
    this.objectUrlApi = objectUrlApi;
  }

  get(key: string): string | undefined {
    return this.objectUrls.get(key);
  }

  load(
    key: string,
    path: string,
    schoolId: number,
    download: ProtectedUpdatePhotoDownload
  ): Promise<string> {
    const cached = this.objectUrls.get(key);
    if (cached) return Promise.resolve(cached);

    const pending = this.inFlight.get(key);
    if (pending) return pending;

    const requestGeneration = this.generation;
    const request = download(path, {
      headers: { 'X-School-Id': String(schoolId) }
    })
      .then((blob) => {
        if (!blob.size || !blob.type.startsWith('image/')) {
          throw new Error('Protected media response was not an image.');
        }
        if (requestGeneration !== this.generation) {
          throw new ProtectedUpdatePhotoClearedError();
        }
        const objectUrl = this.objectUrlApi.createObjectURL(blob);
        this.objectUrls.set(key, objectUrl);
        return objectUrl;
      })
      .finally(() => {
        if (this.inFlight.get(key) === request) {
          this.inFlight.delete(key);
        }
      });

    this.inFlight.set(key, request);
    return request;
  }

  clear(): void {
    this.generation += 1;
    for (const objectUrl of this.objectUrls.values()) {
      this.objectUrlApi.revokeObjectURL(objectUrl);
    }
    this.objectUrls.clear();
    this.inFlight.clear();
  }
}
