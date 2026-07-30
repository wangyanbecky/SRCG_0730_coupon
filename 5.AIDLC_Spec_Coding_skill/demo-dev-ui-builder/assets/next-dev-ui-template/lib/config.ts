import { promises as fs } from "fs";
import path from "path";

export type DemoUiConfig = {
  endpoints: {
    apiBaseUrl: string;
    healthUrl: string;
    queryUrl: string;
    testSessionUrl: string;
    tokenRotationUrl?: string;
  };
  runtime: {
    pollingIntervalMs: number;
    requestTimeoutMs: number;
    maxLogEntries: number;
    largeRequestThresholdKb: number;
  };
  features: {
    debugLogging: boolean;
    mockMode: boolean;
    autoReconnect: boolean;
  };
};

const defaultConfig: DemoUiConfig = {
  endpoints: {
    apiBaseUrl: "http://localhost:8080",
    healthUrl: "http://localhost:8080/health",
    queryUrl: "http://localhost:8080/query",
    testSessionUrl: "http://localhost:8080/test/session",
    tokenRotationUrl: ""
  },
  runtime: {
    pollingIntervalMs: 10000,
    requestTimeoutMs: 15000,
    maxLogEntries: 500,
    largeRequestThresholdKb: 512
  },
  features: {
    debugLogging: true,
    mockMode: false,
    autoReconnect: true
  }
};

export function configPath() {
  return path.resolve(process.cwd(), process.env.DEMO_UI_CONFIG_PATH ?? "config/local.config.json");
}

export async function readConfig(): Promise<DemoUiConfig> {
  try {
    const raw = await fs.readFile(configPath(), "utf8");
    return { ...defaultConfig, ...JSON.parse(raw) };
  } catch {
    await writeConfig(defaultConfig);
    return defaultConfig;
  }
}

export async function writeConfig(config: DemoUiConfig) {
  const file = configPath();
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, `${JSON.stringify(config, null, 2)}\n`, "utf8");
}
