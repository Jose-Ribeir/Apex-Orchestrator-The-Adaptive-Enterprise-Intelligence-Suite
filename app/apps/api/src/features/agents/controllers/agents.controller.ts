import { Request, Response } from "express";
import { paginatedResponse, parsePageLimit } from "../../../lib/pagination";
import { paramUuid } from "../../../lib/params";
import { AgentMode } from "../../../models/Agent";
import { agentService } from "../services/agents.service";

export const agentsController = {
  list: async (req: Request, res: Response) => {
    const { page, limit } = parsePageLimit(req);
    const { data, total } = await agentService.listByUser(req.user!.id, {
      page,
      limit,
    });
    res.json(paginatedResponse(data, total, page, limit));
  },

  getById: async (req: Request, res: Response) => {
    const agent = await agentService.getById(
      paramUuid(req.params.id),
      req.user!.id,
    );
    res.json(agent);
  },

  create: async (req: Request, res: Response) => {
    const body = req.body as {
      name: string;
      mode?: string;
      prompt?: string | null;
      instructions?: string[];
      tools?: string[];
    };
    const agent = await agentService.create({
      userId: req.user!.id,
      name: body.name,
      mode: body.mode as AgentMode,
      prompt: body.prompt,
      instructions: body.instructions,
      tools: body.tools,
    });
    res.status(201).json(agent);
  },

  update: async (req: Request, res: Response) => {
    const body = req.body as {
      name?: string;
      mode?: string;
      prompt?: string | null;
      instructions?: string[];
      tools?: string[];
    };
    const agent = await agentService.update(
      paramUuid(req.params.id),
      req.user!.id,
      {
        name: body.name,
        mode: body.mode as AgentMode,
        prompt: body.prompt,
        instructions: body.instructions,
        tools: body.tools,
      },
    );
    res.json(agent);
  },

  delete: async (req: Request, res: Response) => {
    await agentService.delete(paramUuid(req.params.id), req.user!.id);
    res.status(204).send();
  },
};
