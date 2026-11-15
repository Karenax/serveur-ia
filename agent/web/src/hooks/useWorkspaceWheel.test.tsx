import { useRef } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { useWorkspaceWheel } from "./useWorkspaceWheel";

let originalHeight: PropertyDescriptor | undefined;
let originalClient: PropertyDescriptor | undefined;
beforeEach(() => {
  originalHeight=Object.getOwnPropertyDescriptor(document.documentElement,"scrollHeight");
  originalClient=Object.getOwnPropertyDescriptor(document.documentElement,"clientHeight");
  Object.defineProperty(document.documentElement,"scrollHeight",{configurable:true,value:2000});
  Object.defineProperty(document.documentElement,"clientHeight",{configurable:true,value:720});
  vi.spyOn(window,"scrollBy").mockImplementation(()=>{});
});
afterEach(() => {
  cleanup();vi.restoreAllMocks();
  for(const [key,value] of [["scrollHeight",originalHeight],["clientHeight",originalClient]] as const) {
    if(value)Object.defineProperty(document.documentElement,key,value);else delete (document.documentElement as any)[key];
  }
});
function Harness() {
  const root=useRef<HTMLDivElement>(null);useWorkspaceWheel(root);
  return <div ref={root}><div data-testid="pane" style={{overflowY:"auto"}}><button>Élément</button></div><select aria-label="Choix"><option>Option</option></select></div>;
}
function wheel(target:Element,options:WheelEventInit={}) {
  const event=new WheelEvent("wheel",{deltaY:100,bubbles:true,cancelable:true,...options});
  target.dispatchEvent(event);return event;
}
it("fait défiler la page au-dessus d’une zone qui ne défile que horizontalement", () => {
  render(<Harness/>);
  const pane=screen.getByTestId("pane");
  Object.defineProperties(pane,{clientHeight:{value:300},scrollHeight:{value:300}});
  expect(wheel(screen.getByRole("button")).defaultPrevented).toBe(true);
  expect(window.scrollBy).toHaveBeenCalledWith({top:100,behavior:"instant"});
});
it("conserve le défilement natif d’une liste puis transmet la molette à la page à sa limite", () => {
  render(<Harness/>);
  const pane=screen.getByTestId("pane");
  Object.defineProperties(pane,{clientHeight:{value:300},scrollHeight:{value:1000}});
  pane.scrollTop=200;
  expect(wheel(screen.getByRole("button")).defaultPrevented).toBe(false);
  expect(window.scrollBy).not.toHaveBeenCalled();
  pane.scrollTop=700;
  expect(wheel(screen.getByRole("button")).defaultPrevented).toBe(true);
  expect(window.scrollBy).toHaveBeenCalledOnce();
  pane.scrollTop=0;
  expect(wheel(screen.getByRole("button"),{deltaY:-100}).defaultPrevented).toBe(false);
});
it("préserve le zoom, le défilement horizontal et les sélecteurs", () => {
  render(<Harness/>);
  const button=screen.getByRole("button");
  for(const options of [{ctrlKey:true},{shiftKey:true},{deltaX:150}])expect(wheel(button,options).defaultPrevented).toBe(false);
  expect(wheel(screen.getByLabelText("Choix")).defaultPrevented).toBe(false);
  expect(window.scrollBy).not.toHaveBeenCalled();
});
