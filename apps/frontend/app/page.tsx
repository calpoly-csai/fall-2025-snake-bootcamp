"use client";

import { useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client";

const HEADER_HEIGHT_PX = 64;

type SnakeBody = [number, number][];
type FoodPos = [number, number];

export default function Home() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const socketRef = useRef<Socket | undefined>(undefined);

  // TODO: variables for tracking the snake attributes
  // Use refs (not state) to avoid re-rendering on every tick.
  const gridWRef = useRef<number>(29);
  const gridHRef = useRef<number>(19);
  const scoreRef = useRef<number>(0);
  const snakeRef = useRef<SnakeBody>([[12, 11]]);
  const foodRef = useRef<FoodPos>([7, 8]);
  const cellSizeRef = useRef<number>(20); // computed later
  const paddingRef = useRef<number>(8); // canvas padding for aesthetics

  // Keep a simple draw trigger that we call whenever new data arrives or layout changes.
  const drawRef = useRef<() => void>(() => {});

  useEffect(() => {
    if (socketRef.current === undefined) {
      // Match your server default (change if needed)
      socketRef.current = io("http://localhost:8765", {
        transports: ["websocket"],
      });

      const onConnect = () => {
        socketRef.current?.emit("start_game", {
          // TODO: data about initial game setup
          grid_width: gridWRef.current,
          grid_height: gridHRef.current,
          starting_tick: 0.03,
        });
      };

      // Helper to normalize payloads from either `to_dict()` (init) or `send()` (tick)
      const applyPayload = (payload: any) => {
        // Grid may only appear in init payloads
        if (typeof payload?.grid_width === "number") gridWRef.current = payload.grid_width;
        if (typeof payload?.grid_height === "number") gridHRef.current = payload.grid_height;

        // Snake can be list or { body: ... }
        const snakeRaw = payload?.snake;
        if (Array.isArray(snakeRaw)) {
          snakeRef.current = snakeRaw as SnakeBody;
        } else if (snakeRaw && Array.isArray(snakeRaw.body)) {
          snakeRef.current = snakeRaw.body as SnakeBody;
        }

        // Food can be list or { position: ... }
        const foodRaw = payload?.food;
        if (Array.isArray(foodRaw)) {
          foodRef.current = foodRaw as FoodPos;
        } else if (foodRaw && Array.isArray(foodRaw.position)) {
          foodRef.current = foodRaw.position as FoodPos;
        }

        if (typeof payload?.score === "number") {
          scoreRef.current = payload.score;
        }

        // draw fresh frame
        drawRef.current();
      };

      const onUpdate = (data: any) => {
        // TODO: update the snake and food state based on data from server
        // Some servers emit a flat "update"; handle as a direct payload.
        applyPayload(data);
      };

      // Our backend emits "game_state" with { event, payload }
      const onGameState = (data: any) => {
        const payload = data?.payload ?? data;
        applyPayload(payload);
      };

      const onGameOver = (data: any) => {
        const payload = data?.payload ?? data;
        applyPayload(payload);
        // Optionally leave the last frame on screen
        // You can also show a toast or overlay here.
      };

      socketRef.current.on("connect", onConnect);
      socketRef.current.on("update", onUpdate);        // if server uses 'update'
      socketRef.current.on("game_state", onGameState); // if server uses 'game_state'
      socketRef.current.on("game_over", onGameState);  // render the final frame

      return () => {
        socketRef.current?.off("connect", onConnect);
        socketRef.current?.off("update", onUpdate);
        socketRef.current?.off("game_state", onGameState);
        socketRef.current?.off("game_over", onGameOver);
        socketRef.current?.disconnect();
      };
    }
  }, []); // socket stuff

  // TODO: function to draw the data to the screen
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");

    if (!canvas || !ctx) {
      console.warn("Canvas 2D context is not available");
      return;
    }

    const computeCanvasSize = () => {
      // Leave room for header, keep canvas inside viewport
      const availW = Math.floor(window.innerWidth);
      const availH = Math.floor(window.innerHeight - HEADER_HEIGHT_PX);

      // Compute cell size so the entire grid fits with padding
      const pw = paddingRef.current * 2;
      const ph = paddingRef.current * 2;
      const cellW = Math.floor((availW - pw) / Math.max(1, gridWRef.current));
      const cellH = Math.floor((availH - ph) / Math.max(1, gridHRef.current));
      const cellSize = Math.max(4, Math.min(cellW, cellH)); // minimum visible size

      // Final canvas size snapped to grid
      const width = cellSize * gridWRef.current + pw;
      const height = cellSize * gridHRef.current + ph;

      canvas.width = width;
      canvas.height = height;
      cellSizeRef.current = cellSize;
    };

    const colors = () => {
      // Simple theme adapt: check for Tailwind's `.dark` class
      const isDark = document.documentElement.classList.contains("dark");
      return {
        bg: isDark ? "#0B0B0C" : "#FFFFFF",
        grid: isDark ? "#1F2937" : "#E5E7EB",
        snake: isDark ? "#34D399" : "#059669",
        food: isDark ? "#F87171" : "#DC2626",
        text: isDark ? "#F8FAFC" : "#0F172A",
      };
    };

    const draw = () => {
      computeCanvasSize();
      const { bg, grid, snake, food, text } = colors();
      const cell = cellSizeRef.current;
      const pad = paddingRef.current;

      // TODO: clear the canvas before drawing more
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Fill background
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // TODO: draw the info
      // 1) Grid (subtle)
      ctx.strokeStyle = grid;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = 0; x <= gridWRef.current; x++) {
        const px = pad + x * cell + 0.5;
        ctx.moveTo(px, pad);
        ctx.lineTo(px, pad + gridHRef.current * cell);
      }
      for (let y = 0; y <= gridHRef.current; y++) {
        const py = pad + y * cell + 0.5;
        ctx.moveTo(pad, py);
        ctx.lineTo(pad + gridWRef.current * cell, py);
      }
      ctx.stroke();

      // 2) Snake
      ctx.fillStyle = snake;
      for (const [sx, sy] of snakeRef.current) {
        ctx.fillRect(pad + sx * cell, pad + sy * cell, cell, cell);
      }

      // 3) Food
      const [fx, fy] = foodRef.current;
      ctx.fillStyle = food;
      const r = Math.floor(cell / 2);
      ctx.beginPath();
      ctx.arc(
        pad + fx * cell + cell / 2,
        pad + fy * cell + cell / 2,
        Math.max(2, r * 0.6),
        0,
        Math.PI * 2
      );
      ctx.fill();

      // 4) Score (top-left)
      ctx.fillStyle = text;
      ctx.font = `bold ${Math.max(12, Math.floor(cell * 0.8))}px ui-sans-serif, system-ui`;
      ctx.fillText(`Score: ${scoreRef.current}`, pad, Math.max(18, pad + cell));
    };

    // bind the draw function for external triggers
    drawRef.current = draw;

    // Initial paint
    draw();

    const observer = new MutationObserver(() => {
      // TODO: handle redwaring on theme change
      drawRef.current();
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => {
      observer.disconnect();
    };
  }, []); // redraw

  useEffect(() => {
    const handleResize = () => {
      // TODO: maybe manage canvas on resize
      // Recompute canvas dimensions and redraw with current state
      drawRef.current();
    };

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []); // resize

  return (
    <div className="absolute top-16 left-0 right-0 bottom-0 flex flex-col items-center justify-center">
      <canvas
        ref={canvasRef}
        // width/height are managed programmatically to fit the grid & viewport
        style={{ position: "absolute", border: "none", outline: "none" }}
      />
      <div className="absolute rounded-lg p-8 w-fit flex flex-col items-center shadow-md backdrop-blur-md bg-background-trans">
        <span className="text-primary text-3xl font-extrabold mb-2 text-center">
          CSAI Student
        </span>
      </div>
    </div>
  );
}
