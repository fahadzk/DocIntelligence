import { Button } from "./Button";
export function ErrorState({ message, retry }: { message: string; retry?: () => void }) { return <div className="error-state" role="alert"><strong>Unable to load the workspace</strong><span>{message}</span>{retry && <Button onClick={retry}>Try again</Button>}</div>; }
