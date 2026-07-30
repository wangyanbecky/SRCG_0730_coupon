import {
  BedrockClient,
  ListFoundationModelsCommand,
} from '@aws-sdk/client-bedrock';
import {
  BedrockRuntimeClient,
  ConverseCommand,
} from '@aws-sdk/client-bedrock-runtime';
import { ModelInfo, ConverseResult } from '../types';

const DEFAULT_TIMEOUT_MS = 10_000;
const CONVERSE_TIMEOUT_MS = 60_000;

export class BedrockService {
  private client: BedrockRuntimeClient;
  private bedrockClient: BedrockClient;

  constructor(region?: string) {
    const config = { region: region ?? process.env.AWS_REGION ?? 'us-east-1' };
    this.client = new BedrockRuntimeClient(config);
    this.bedrockClient = new BedrockClient(config);
  }

  /**
   * Retrieves the list of Bedrock foundation models that support text output.
   * Uses SDK credentials only. API Key mode uses static config file (handled in route).
   */
  async listTextModels(): Promise<ModelInfo[]> {
    const command = new ListFoundationModelsCommand({});

    const abortController = new AbortController();
    const timeout = setTimeout(() => abortController.abort(), DEFAULT_TIMEOUT_MS);

    try {
      const response = await this.bedrockClient.send(command, {
        abortSignal: abortController.signal,
      });

      const modelSummaries = response.modelSummaries ?? [];

      // Filter models that have "TEXT" in their outputModalities
      const textModels = modelSummaries.filter((model) =>
        model.outputModalities?.includes('TEXT')
      );

      // Map to ModelInfo interface
      const allModels = textModels.map((model) => ({
        modelId: model.modelId ?? '',
        modelName: model.modelName ?? '',
        provider: model.providerName ?? '',
        inputModalities: model.inputModalities ?? [],
        outputModalities: model.outputModalities ?? [],
      }));

      // Deduplicate by modelName - keep the shortest modelId variant per name
      const seen = new Map<string, typeof allModels[number]>();
      for (const model of allModels) {
        const key = `${model.provider}::${model.modelName}`;
        const existing = seen.get(key);
        if (!existing || model.modelId.length < existing.modelId.length) {
          seen.set(key, model);
        }
      }
      return Array.from(seen.values());
    } catch (error: unknown) {
      if (
        error instanceof Error &&
        (error.name === 'AbortError' || error.name === 'TimeoutError')
      ) {
        throw new Error('Bedrock ListFoundationModels request timed out');
      }
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * Sends a conversation to the Bedrock Converse API.
   * Two completely separate paths:
   * - SDK credentials: uses BedrockRuntimeClient + ConverseCommand
   * - API Key: uses raw HTTP request with Bearer token authorization
   */
  async converse(
    modelId: string,
    messages: Array<{ role: 'user' | 'assistant'; content: string }>,
    apiKey?: string,
    region?: string
  ): Promise<ConverseResult> {
    if (apiKey) {
      return this.converseWithApiKey(modelId, messages, apiKey, region);
    }
    return this.converseWithSdk(modelId, messages);
  }

  /**
   * SDK credentials path: uses BedrockRuntimeClient.
   */
  private async converseWithSdk(
    modelId: string,
    messages: Array<{ role: 'user' | 'assistant'; content: string }>
  ): Promise<ConverseResult> {
    const converseMessages = messages.map((msg) => ({
      role: msg.role as 'user' | 'assistant',
      content: [{ text: msg.content }],
    }));

    const command = new ConverseCommand({
      modelId,
      messages: converseMessages,
    });

    const abortController = new AbortController();
    const timeout = setTimeout(() => abortController.abort(), CONVERSE_TIMEOUT_MS);

    try {
      const response = await this.client.send(command, {
        abortSignal: abortController.signal,
      });

      const outputMessage = response.output?.message;
      const content = outputMessage?.content?.[0]?.text ?? '';
      const inputTokens = response.usage?.inputTokens ?? null;
      const outputTokens = response.usage?.outputTokens ?? null;

      return {
        content,
        tokenUsage: { inputTokens, outputTokens },
      };
    } catch (error: unknown) {
      if (error instanceof Error) {
        console.error('[BedrockService.converseWithSdk] Error:', error.name, error.message);
      }

      if (
        error instanceof Error &&
        (error.name === 'AbortError' || error.name === 'TimeoutError')
      ) {
        throw new Error('Bedrock Converse request timed out after 60 seconds');
      }

      if (
        error instanceof Error &&
        error.name === 'ValidationException'
      ) {
        throw new Error(`Context limit exceeded: ${error.message}`);
      }

      if (
        error instanceof Error &&
        error.name === 'AccessDeniedException'
      ) {
        throw new Error(`模型访问被拒绝: ${error.message}`);
      }

      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * API Key path: uses raw HTTP POST with Bearer token.
   * Directly calls the Bedrock Runtime REST API endpoint.
   * Endpoint format: https://bedrock-runtime.{region}.amazonaws.com/model/{modelId}/converse
   */
  private async converseWithApiKey(
    modelId: string,
    messages: Array<{ role: 'user' | 'assistant'; content: string }>,
    apiKey: string,
    region?: string
  ): Promise<ConverseResult> {
    const targetRegion = region ?? process.env.AWS_REGION ?? 'us-east-1';
    const url = `https://bedrock-runtime.${targetRegion}.amazonaws.com/model/${encodeURIComponent(modelId)}/converse`;

    const payload = {
      messages: messages.map((msg) => ({
        role: msg.role,
        content: [{ text: msg.content }],
      })),
    };

    const abortController = new AbortController();
    const timeout = setTimeout(() => abortController.abort(), CONVERSE_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
        },
        body: JSON.stringify(payload),
        signal: abortController.signal,
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const body: any = await response.json();

      if (!response.ok) {
        console.error('[BedrockService.converseWithApiKey] HTTP Error:', response.status, JSON.stringify(body));
        const errorMessage: string = body?.message || body?.Message || 'Unknown error';

        if (response.status === 403 || response.status === 401) {
          throw new Error('Invalid Bedrock API Key. Please check your key and try again.');
        }

        if (response.status === 400 && errorMessage.includes('context')) {
          throw new Error(`Context limit exceeded: ${errorMessage}`);
        }

        if (response.status === 400) {
          throw new Error(`请求错误: ${errorMessage}`);
        }

        if (response.status === 404) {
          throw new Error(`模型不存在或未开通: ${modelId}`);
        }

        if (response.status === 429) {
          throw new Error('请求频率过高，请稍后再试。');
        }

        throw new Error(`Bedrock API 错误 (${response.status}): ${errorMessage}`);
      }

      // Parse successful response
      const content: string = body?.output?.message?.content?.[0]?.text ?? '';
      const inputTokens: number | null = body?.usage?.inputTokens ?? null;
      const outputTokens: number | null = body?.usage?.outputTokens ?? null;

      return {
        content,
        tokenUsage: { inputTokens, outputTokens },
      };
    } catch (error: unknown) {
      if (error instanceof Error) {
        // Re-throw our own errors
        if (error.message.includes('Invalid Bedrock API Key') ||
            error.message.includes('Context limit exceeded') ||
            error.message.includes('模型') ||
            error.message.includes('请求') ||
            error.message.includes('Bedrock API')) {
          throw error;
        }

        if (error.name === 'AbortError') {
          throw new Error('Bedrock Converse request timed out after 60 seconds');
        }

        console.error('[BedrockService.converseWithApiKey] Error:', error.name, error.message);
      }

      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }
}
