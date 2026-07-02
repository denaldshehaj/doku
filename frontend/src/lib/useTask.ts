/* Polls a background task (reindex-all, experiment batches) until it finishes.
 * The API returns the TaskInfo immediately; this hook follows its progress. */
import { useCallback, useEffect, useRef, useState } from "react";
import { tasksApi } from "@/api/endpoints";
import type { TaskInfo } from "@/api/types";

const POLL_MS = 1500;

export function useTask(onFinished?: (task: TaskInfo) => void) {
  const [task, setTask] = useState<TaskInfo | null>(null);
  const timer = useRef<number | null>(null);
  const finishedCb = useRef(onFinished);
  finishedCb.current = onFinished;

  const stop = useCallback(() => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  const track = useCallback((initial: TaskInfo) => {
    stop();
    setTask(initial);
    timer.current = window.setInterval(async () => {
      try {
        const t = await tasksApi.get(initial.id);
        setTask(t);
        if (t.status !== "running") {
          stop();
          finishedCb.current?.(t);
        }
      } catch {
        stop(); // task evicted or session lost — stop polling quietly
      }
    }, POLL_MS);
  }, [stop]);

  const clear = useCallback(() => {
    stop();
    setTask(null);
  }, [stop]);

  useEffect(() => stop, [stop]);

  return { task, track, clear, running: task?.status === "running" };
}
