"""이 과정은 모든 Deep Agent를 프레임워크가 자동으로 붙이는 general-purpose 하위 에이전트 없이 만든다.

그 에이전트는 부모의 도구를 받지만 부모의 사용자 정의 middleware는 받지 않는다. 그래서 이 과정의 허용 목록과
공유 예산이 적용되지 않는다 (02 3절). 노트북은 첫 코드 셀에서 `mas_lab`을 import하므로, 노트북이 직접
부르는 `create_deep_agent`에도 이 설정이 적용된다.
"""
from mas_lab.harness import use_designed_subagents_only

use_designed_subagents_only()
