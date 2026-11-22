"""Run the local workbench with optional AgentArts IAM authentication."""

import argparse
import getpass
import os
import warnings

from . import create_app
from .agentarts import AgentArtsChat

DEFAULT_ENDPOINT = "https://defaultgw-mjrwiobqhe.cn-southwest-2.huaweicloud-agentarts.com"


def main():
    parser = argparse.ArgumentParser(description="Run the research library on 127.0.0.1.")
    parser.add_argument("--agentarts", action="store_true", help="Enable AgentArts QA using Huawei Cloud IAM.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--agent", default="agent-huawei-cit")
    parser.add_argument("--region", default="cn-southwest-2")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    config = {}
    if args.agentarts:
        ak = os.environ.get("HUAWEICLOUD_SDK_AK", "").strip()
        sk = os.environ.get("HUAWEICLOUD_SDK_SK", "").strip()
        token = os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN", "").strip()
        try:
            if not (ak and sk):
                if ak or sk or token:
                    raise ValueError("请同时设置 AK 和 SK，或清除相关环境变量后使用隐藏输入。")
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    ak = getpass.getpass("Huawei Cloud AK (hidden): ").strip()
                    sk = getpass.getpass("Huawei Cloud SK (hidden): ").strip()
            config["AGENTARTS_CLIENT"] = AgentArtsChat(args.endpoint, args.agent, args.region, ak, sk, token)
        except (EOFError, getpass.GetPassWarning):
            parser.error("无法隐藏输入。请在本机交互式 PowerShell 中运行。")
        except ValueError as error:
            parser.error(str(error))
    create_app(config).run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()