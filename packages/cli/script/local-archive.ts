import path from "node:path"
import { brotliCompressSync, constants } from "node:zlib"
import { writeFileSync } from "node:fs"
import { AppArchive } from "../src/app-archive"
import { collectFiles } from "./files"

const root = path.resolve(import.meta.dirname, "../../app")
const out = process.argv[2] ?? path.resolve(import.meta.dirname, "../../../app-archive.local.bin")
const files = (await collectFiles(path.join(root, "dist")))
  .map((k) => k.replaceAll(path.sep, "/"))
  .filter((k) => !k.endsWith(".map"))
  .toSorted()
const entries: Array<readonly [string, Uint8Array]> = []
for (const key of files) {
  const body = Buffer.from(await Bun.file(path.join(root, "dist", key)).arrayBuffer())
  const compressed = brotliCompressSync(body, {
    params: {
      [constants.BROTLI_PARAM_QUALITY]: 6,
      [constants.BROTLI_PARAM_SIZE_HINT]: body.length,
    },
  })
  entries.push([key, compressed] as const)
}
const archive = AppArchive.encode(entries)
writeFileSync(out, archive)
console.log("wrote", out, archive.length, "bytes from", entries.length, "assets")
