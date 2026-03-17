const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");
const http = require("http");
const https = require("https");
const { URL } = require("url");

class CWClient {
  constructor() {
    const baseUrl = process.env.INTERLEAVED_THINKING_API_URL || "https://abcd.bpjwmsdb.com";
    const timeoutVal = Number.parseFloat(process.env.INTERLEAVED_THINKING_TIMEOUT || "3000");
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.timeoutMs = Number.isFinite(timeoutVal) ? timeoutVal * 1000 : 3000000;
    this.apiKey = this.loadApiKey();
    this.editorProtocol = process.env.EDITOR_PROTOCOL || this.loadEditorProtocol();
  }

  loadApiKey() {
    const key = process.env.CONTEXTWEAVE_MCP_API_KEY || process.env.MCP_API_KEY;
    if (key) {
      return key;
    }
    const configPaths = [
      path.join(process.cwd(), "cwmcp_config.json"),
      path.join(os.homedir(), ".cwmcp", "config.json"),
      "cwmcp_config.json",
    ];
    for (const configPath of configPaths) {
      if (!fs.existsSync(configPath)) {
        continue;
      }
      try {
        const data = JSON.parse(fs.readFileSync(configPath, "utf8"));
        const cfgKey = data.api_key;
        if (cfgKey) {
          return cfgKey;
        }
      } catch (error) {
      }
    }
    return null;
  }

  loadEditorProtocol() {
    const configPaths = [
      path.join(process.cwd(), "cwmcp_config.json"),
      path.join(os.homedir(), ".cwmcp", "config.json"),
      "cwmcp_config.json",
    ];
    for (const configPath of configPaths) {
      if (!fs.existsSync(configPath)) {
        continue;
      }
      try {
        const data = JSON.parse(fs.readFileSync(configPath, "utf8"));
        const protocol = data.editor_protocol;
        if (protocol) {
          return protocol;
        }
      } catch (error) {
      }
    }
    return null;
  }

  headers() {
    const headers = { "X-Request-ID": this.createRequestId(), "Content-Type": "application/json" };
    if (this.apiKey) {
      headers["X-API-Key"] = this.apiKey;
    }
    return headers;
  }

  createRequestId() {
    return crypto.randomBytes(16).toString("hex");
  }

  error(code, message, recoverable = false, recoveryHint = null) {
    const result = { status: "error", error: { code, message } };
    if (recoverable) {
      result.error.recoverable = true;
    }
    if (recoveryHint) {
      result.error.recovery_hint = recoveryHint;
    }
    return result;
  }

  async request(endpoint, payload) {
    const body = { ...payload };
    if (this.editorProtocol) {
      body.editor_protocol = this.editorProtocol;
    }

    try {
      const response = await this.postJson(`${this.baseUrl}${endpoint}`, body);
      if (response.statusCode === 402) {
        return this.error("PAYMENT_REQUIRED", "Insufficient credits", true, "请充值后重试");
      }
      if (response.statusCode === 403) {
        return this.error("AUTH_ERROR", "Invalid API key or missing key", true, "请检查 CONTEXTWEAVE_MCP_API_KEY（兼容 MCP_API_KEY）或配置文件中的 api_key");
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw new Error(`${response.statusCode} ${response.statusMessage || "Request failed"}`);
      }
      return JSON.parse(response.body || "{}");
    } catch (error) {
      return this.error("API_ERROR", String(error.message || error), true, "请检查网络或后端服务状态后重试");
    }
  }

  postJson(urlString, body) {
    const parsed = new URL(urlString);
    const payload = JSON.stringify(body);
    const options = {
      method: "POST",
      hostname: parsed.hostname,
      port: parsed.port || (parsed.protocol === "https:" ? 443 : 80),
      path: `${parsed.pathname}${parsed.search}`,
      headers: {
        ...this.headers(),
        "Content-Length": Buffer.byteLength(payload),
      },
    };
    const transport = parsed.protocol === "https:" ? https : http;
    return new Promise((resolve, reject) => {
      const req = transport.request(options, (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          resolve({
            statusCode: res.statusCode || 0,
            statusMessage: res.statusMessage || "",
            body: Buffer.concat(chunks).toString("utf8"),
          });
        });
      });
      req.setTimeout(this.timeoutMs, () => {
        req.destroy(new Error("timeout"));
      });
      req.on("error", reject);
      req.write(payload);
      req.end();
    });
  }

  async runGeneration({ userRequest, inputFile = null, sessionId = null, mode = "3", inputSequence = null }) {
    const payload = {
      mode,
      input_sequence: inputSequence,
      export_svg: true,
      export_pptx: false,
      session_id: sessionId,
      test_file: null,
    };
    if (inputFile) {
      if (!fs.existsSync(inputFile)) {
        return this.error("FILE_NOT_FOUND", `File not found: ${inputFile}`);
      }
      try {
        const content = fs.readFileSync(inputFile, "utf8");
        let reqText = content.trim();
        let d2Text = "";
        if (content.includes("# D2")) {
          const parts = content.split("# D2");
          const reqPart = parts[0];
          const d2Part = parts.slice(1).join("# D2");
          const afterFence = d2Part.split("```d2")[1];
          if (afterFence && afterFence.includes("```")) {
            d2Text = afterFence.split("```")[0].trim();
          } else {
            d2Text = d2Part.trim();
          }
          if (reqPart.includes("# Request")) {
            reqText = reqPart.split("# Request")[1].trim();
          } else {
            reqText = reqPart.trim();
          }
        }
        payload.user_request = reqText;
        payload.initial_d2_code = d2Text;
      } catch (error) {
        return this.error("READ_ERROR", `Failed to read input file: ${String(error.message || error)}`);
      }
    } else {
      payload.user_request = userRequest;
    }
    return this.request("/run", payload);
  }

  async exportSessionAsset(sessionId, formatName) {
    return this.request("/export-session", { session_id: sessionId, format: formatName });
  }

  async importCode(target = "ContextWeave") {
    const targetPath = path.isAbsolute(target) ? target : path.resolve(target);
    if (!fs.existsSync(targetPath)) {
      return this.error("PATH_NOT_FOUND", `Directory not found: ${targetPath}`);
    }
    let cwFile = path.join(targetPath, "diagram.cw");
    if (!fs.existsSync(cwFile)) {
      let files;
      try {
        files = fs.readdirSync(targetPath).filter((name) => name.endsWith(".cw"));
      } catch (error) {
        return this.error("READ_ERROR", String(error.message || error));
      }
      if (!files.length) {
        return this.error("FILE_NOT_FOUND", `No .cw files found in ${targetPath}`);
      }
      cwFile = path.join(targetPath, files[0]);
    }
    let content;
    try {
      content = fs.readFileSync(cwFile, "utf8");
    } catch (error) {
      return this.error("READ_ERROR", String(error.message || error));
    }
    return this.request("/session/import", { d2_code: content, source_name: cwFile });
  }

  async exportCode(sessionId, target = "ContextWeave") {
    const result = await this.request("/session/export", { session_id: sessionId });
    if (result.status === "error") {
      return result;
    }
    const d2Code = result.d2_code;
    const targetPath = path.isAbsolute(target) ? target : path.resolve(target);
    try {
      fs.mkdirSync(targetPath, { recursive: true });
    } catch (error) {
      return this.error("CREATE_DIR_ERROR", String(error.message || error));
    }
    const targetFile = path.join(targetPath, "diagram.cw");
    try {
      fs.writeFileSync(targetFile, d2Code || "", "utf8");
    } catch (error) {
      return this.error("WRITE_ERROR", String(error.message || error));
    }
    return { status: "ok", file_path: targetFile, session_id: sessionId };
  }
}

function printJson(data) {
  process.stdout.write(`${JSON.stringify(data, null, 2)}\n`);
}

module.exports = {
  CWClient,
  printJson,
};
