# 编辑状态
self._edit_mode = False
self._temp_waypoint_items = []
self._preview_line_item = None
self._preview_last_pos = None
self._undo_stack = []          # 新增：撤销快照栈
