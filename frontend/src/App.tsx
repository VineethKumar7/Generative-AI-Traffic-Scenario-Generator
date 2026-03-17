import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppLayout from "@/components/AppLayout";
import Dashboard from "@/pages/Dashboard";
import ScenarioBuilder from "@/pages/ScenarioBuilder";
import AIGenerator from "@/pages/AIGenerator";
import BatchGenerator from "@/pages/BatchGenerator";
import ScenarioLibrary from "@/pages/ScenarioLibrary";
import Simulator from "@/pages/Simulator";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/builder" element={<ScenarioBuilder />} />
            <Route path="/ai-generate" element={<AIGenerator />} />
            <Route path="/batch" element={<BatchGenerator />} />
            <Route path="/library" element={<ScenarioLibrary />} />
            <Route path="/simulator" element={<Simulator />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
