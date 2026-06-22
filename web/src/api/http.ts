const JSON_HEADERS = {
  "Content-Type": "application/json",
};

const DEFAULT_TIMEOUT_MS = 5000;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const isJson = response.headers.get("content-type")?.includes("application/json");
  if (!response.ok) {
    if (isJson) {
      const payload = await response.json();
      throw new ApiError(String(payload.detail ?? "Request failed"), response.status);
    }
    throw new ApiError(await response.text(), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!isJson) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function createTimeoutSignal(timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => {
    controller.abort(new Error("Request timed out"));
  }, timeoutMs);

  return {
    signal: controller.signal,
    cleanup: () => window.clearTimeout(timer),
  };
}

export async function getJson<T>(url: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const { signal, cleanup } = createTimeoutSignal(timeoutMs);
  try {
    const response = await fetch(url, {
      method: "GET",
      credentials: "include",
      signal,
    });
    return parseResponse<T>(response);
  } finally {
    cleanup();
  }
}

export async function postJson<T>(url: string, payload?: unknown, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const { signal, cleanup } = createTimeoutSignal(timeoutMs);
  try {
    const response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: JSON_HEADERS,
      body: payload === undefined ? undefined : JSON.stringify(payload),
      signal,
    });
    return parseResponse<T>(response);
  } finally {
    cleanup();
  }
}

export async function postForm<T>(url: string, formData: FormData, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const { signal, cleanup } = createTimeoutSignal(timeoutMs);
  try {
    const response = await fetch(url, {
      method: "POST",
      credentials: "include",
      body: formData,
      signal,
    });
    return parseResponse<T>(response);
  } finally {
    cleanup();
  }
}

export async function deleteJson<T>(url: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const { signal, cleanup } = createTimeoutSignal(timeoutMs);
  try {
    const response = await fetch(url, {
      method: "DELETE",
      credentials: "include",
      signal,
    });
    return parseResponse<T>(response);
  } finally {
    cleanup();
  }
}
