"use client";

import { useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";

const HEADER_HEIGHT_PX = 64;

export default function Home() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const socketRef = useRef<Socket | undefined>(undefined);

  // TODO: variables for tracking the snake attributes
  const [snake, setSnake] = useState<number[][]>([]);
  const [food, setFood] = useState<number[]>([]);
  const [score, setScore] = useState<number>(0);
  const [gameOver, setGameOver] = useState<boolean>(false);
  const [gridWidth, setGridWidth] = useState<number>(29);
  const [gridHeight, setGridHeight] = useState<number>(19);

  useEffect(() => {
    if (socketRef.current === undefined) {
      socketRef.current = io("localhost:8000"); // ← Should be 8000

      const onConnect = () => {
        socketRef.current?.emit("start_game", {
          grid_width: 20,
          grid_height: 20,
          starting_tick: 200,
        });
      };

      const onUpdate = (data: unknown) => {
        const { snake, food, score, game_over, grid_width, grid_height } =
          data as {
            snake: number[][];
            food: number[];
            score: number;
            game_over: boolean;
            grid_width?: number;
            grid_height?: number;
          };

        setSnake(snake);
        setFood(food);
        setScore(score);
        setGameOver(game_over);
        if (grid_width) setGridWidth(grid_width);
        if (grid_height) setGridHeight(grid_height);
      };

      socketRef.current.on("connect", onConnect);
      socketRef.current.on("game_state", onUpdate);

      return () => {
        socketRef.current?.off("connect", onConnect);
        socketRef.current?.off("game_state", onUpdate);
      };
    }
  }, []); // socket stuff

  // TODO: function to draw the data to the screen
  const draw = () => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");

    if (!context || !canvas) return;

    // Don't draw if no data yet
    if (snake.length === 0) return;

    // Clear the canvas before drawing
    context.clearRect(0, 0, canvas.width, canvas.height);

    const cellSize = canvas.width / gridWidth; // Use actual grid width from backend
    context.fillStyle = "#4ade80";
    snake.forEach(([x, y]) => {
      context.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
    });

    // Only draw food if it exists
    if (food.length === 2) {
      context.fillStyle = "#ef4444";
      context.fillRect(
        food[0] * cellSize,
        food[1] * cellSize,
        cellSize,
        cellSize
      );
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");

    if (!context || !canvas) {
      console.warn("Canvas 2D context is not available");
      return;
    }

    // TODO: clear the canvas before drawing more
    context.clearRect(0, 0, canvas.width, canvas.height);
    // TODO: draw the info
    draw();

    const observer = new MutationObserver(() => {
      // TODO: handle redwaring on theme change
      draw();
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => {
      observer.disconnect();
    };
  }, [snake, food]); // redraw when snake or food changes

  useEffect(() => {
    const handleResize = () => {
      // TODO: maybe manage canvas on resize
      draw();
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
        width={580}
        height={380}
        style={{
          position: "absolute",
          border: "2px solid #888",
          outline: "none",
        }}
      />
    </div>
  );
}
