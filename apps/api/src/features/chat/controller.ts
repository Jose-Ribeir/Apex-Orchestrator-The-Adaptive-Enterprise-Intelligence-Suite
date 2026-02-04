import { Request, Response } from "express";

export interface ChatStreamBody {
  agentId: string;
  message: string;
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const chatController = {
  stream: async (req: Request, res: Response): Promise<void> => {
    await delay(2000);
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.send("UNDER DEVELOPMENT");
  },
};
