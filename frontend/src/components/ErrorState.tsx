import { Button } from "./Button";
import { Icon } from "./Icon";
export function ErrorState({ message, retry, title = "Something went wrong" }: { message: string; retry?: () => void; title?: string }) {
  return <div className="error-state" role="alert"><Icon name="error" size={20} /><div><strong>{title}</strong><p>{message}</p>{retry && <Button icon="refresh" onClick={retry}>Try again</Button>}</div></div>;
}
