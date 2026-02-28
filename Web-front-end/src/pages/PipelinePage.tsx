import { useNavigate } from "react-router-dom";
import { GitBranch } from "lucide-react";
import { Button } from "../components/Button";

export function PipelinePage() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4 text-center">
      <div className="p-4 bg-blue-50 rounded-full">
        <GitBranch size={40} className="text-blue-500" />
      </div>
      <h1 className="text-2xl font-bold text-gray-900">Pipeline</h1>
      <p className="text-gray-500 max-w-sm">
        This page will show deals you've sent to the next stage of your workflow.
        <br />
        <span className="text-sm text-gray-400 mt-1 block">Coming soon.</span>
      </p>
      <Button variant="secondary" onClick={() => navigate("/")}>
        Back to Saved Searches
      </Button>
    </div>
  );
}
