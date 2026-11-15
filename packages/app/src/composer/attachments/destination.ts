import type { Accessor } from "solid-js"
import { useServer } from "@/runtime/server/current"
import { useServerSDK } from "@/runtime/server/client"
import { authTokenFromCredentials } from "@/runtime/server/api"
import { uuid } from "@opencode/util/uuid"
import { useWorkspaceLocation } from "@/workspaces/location"
import type { ComposerControls } from "../adapter"

// Where a prompt is headed: the model that reads it and the server that runs its tools.
export type AttachmentDestination = {
  /** Input modalities the selected model reads natively. */
  input: { image: boolean; pdf: boolean }
  /** The server shares the client's filesystem, so an attachment's source path resolves as-is. */
  local: boolean
  /** Streams a file into the server's temporary directory and returns its absolute path there. */
  upload: (file: File, report: (loaded: number) => void, signal: AbortSignal) => Promise<string>
}

export function useAttachmentDestination(controls: Accessor<ComposerControls>) {
  const server = useServer()
  const sdk = useServerSDK()
  const location = useWorkspaceLocation()

  return (): AttachmentDestination => {
    // capabilities.input is the broad modality list from the model catalog
    // ("text", "image", "pdf", ...). Servers have shipped both an array and a
    // comma-separated string here; calling .some on the string was the
    // "i.some is not a function" crash when adding an image. Normalize both
    // shapes before deciding whether the model accepts the attachment.
    const selected = controls().model.selection.current()
    const value = selected?.capabilities.input as unknown
    // The local AvciCode proxy exposes the upstream multimodal free models, but
    // its /v1/models discovery reports text-only. Treat it as image-capable so
    // the composer inlines images instead of degrading them to file paths.
    const proxied = selected?.providerID === "opencode-unlimited-proxy"
    const known = !proxied && (Array.isArray(value) || typeof value === "string" || (!!value && typeof value === "object"))
    const modalities = !value
      ? []
      : Array.isArray(value)
        ? value.filter((item): item is string => typeof item === "string")
        : typeof value === "string"
          ? value.split(/[,\s]+/).filter(Boolean)
          : Object.entries(value as Record<string, unknown>)
              .filter(([, enabled]) => enabled === true)
              .map(([key]) => key)
    return {
      input: {
        image: !known || modalities.some((item) => item === "image" || item.startsWith("image/")),
        pdf: !known || modalities.some((item) => item === "pdf" || item === "application/pdf"),
      },
      local: server.isLocal,
    upload: async (file, report, signal) => {
      const info = await sdk.api.server.info({ signal })
      // One directory per upload keeps the original filename without collisions; the server
      // normalizes the separators and returns the resolved path.
      const url = new URL("/api/experimental/fs/write", sdk.http.url)
      url.searchParams.set("location[directory]", location().directory)
      url.searchParams.set("path", `${info.paths.tmp}/uploads/${uuid()}/${file.name}`)

      return write(url, file, sdk.http.password, report, signal)
      },
    }
  }
}

// fetch cannot report upload progress and Chromium only streams request bodies over HTTP/2, so
// the one request that needs both goes through XMLHttpRequest. The browser streams the File
// from disk; nothing is buffered in the renderer.
function write(
  url: URL,
  file: File,
  password: string | undefined,
  report: (loaded: number) => void,
  signal: AbortSignal,
) {
  return new Promise<string>((resolve, reject) => {
    if (signal.aborted) return reject(new DOMException("Upload aborted", "AbortError"))
    const xhr = new XMLHttpRequest()
    xhr.open("POST", url)
    xhr.responseType = "json"
    xhr.setRequestHeader("content-type", "application/octet-stream")

    if (password) xhr.setRequestHeader("authorization", `Basic ${authTokenFromCredentials({ password })}`)
    xhr.upload.addEventListener("progress", (event) => report(event.loaded))
    xhr.addEventListener("load", () => {
      if (xhr.status !== 200) return reject(new Error(`Upload failed with status ${xhr.status}`))
      // SAFETY: a 200 from `fs.write` is its declared success body, `Location.response(FileSystem.Write)`.
      resolve((xhr.response as { data: { path: string } }).data.path)
    })
    xhr.addEventListener("error", () => reject(new Error("Upload failed")))
    xhr.addEventListener("abort", () => reject(new DOMException("Upload aborted", "AbortError")))
    signal.addEventListener("abort", () => xhr.abort(), { once: true })
    xhr.send(file)
  })
}
