import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { registerClankerCommand } from "./command.js";

export default function (pi: ExtensionAPI) {
    registerClankerCommand(pi);
    console.log("clanker-ops-v2 activated!");
}
