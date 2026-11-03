path = 'client/src/App.tsx'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. State definition
old_state = '''  const [isArtifactDrawerOpen, setIsArtifactDrawerOpen] = useState(false);
  const [isVisionDrawerOpen, setIsVisionDrawerOpen] = useState(false);
  const [isActivityDrawerOpen, setIsActivityDrawerOpen] = useState(false);'''

new_state = '''  type ActiveDrawer = 'none' | 'artifact' | 'vision' | 'activity';
  const [activeDrawer, setActiveDrawer] = useState<ActiveDrawer>('none');
  const isArtifactDrawerOpen = activeDrawer === 'artifact';
  const isVisionDrawerOpen = activeDrawer === 'vision';
  const isActivityDrawerOpen = activeDrawer === 'activity';'''

assert old_state in content, "old_state not found in App.tsx"
content = content.replace(old_state, new_state)

# 2. Header toggles
old_toggles = '''                isArtifactDrawerOpen={isArtifactDrawerOpen}
                onToggleArtifactDrawer={() => {
                  const next = !isArtifactDrawerOpen;
                  setIsArtifactDrawerOpen(next);
                  if (next) {
                    setIsVisionDrawerOpen(false);
                    setIsActivityDrawerOpen(false);
                  }
                }}
                hasArtifact={!!activeArtifact}
                isVisionDrawerOpen={isVisionDrawerOpen}
                onToggleVisionDrawer={() => {
                  const next = !isVisionDrawerOpen;
                  setIsVisionDrawerOpen(next);
                  if (next) {
                    setIsArtifactDrawerOpen(false);
                    setIsActivityDrawerOpen(false);
                  }
                }}
                isActivityDrawerOpen={isActivityDrawerOpen}
                onToggleActivityDrawer={() => {
                  const next = !isActivityDrawerOpen;
                  setIsActivityDrawerOpen(next);
                  if (next) {
                    setIsVisionDrawerOpen(false);
                    setIsArtifactDrawerOpen(false);
                  }
                }}'''

new_toggles = '''                isArtifactDrawerOpen={isArtifactDrawerOpen}
                onToggleArtifactDrawer={() => setActiveDrawer(prev => prev === 'artifact' ? 'none' : 'artifact')}
                hasArtifact={!!activeArtifact}
                isVisionDrawerOpen={isVisionDrawerOpen}
                onToggleVisionDrawer={() => setActiveDrawer(prev => prev === 'vision' ? 'none' : 'vision')}
                isActivityDrawerOpen={isActivityDrawerOpen}
                onToggleActivityDrawer={() => setActiveDrawer(prev => prev === 'activity' ? 'none' : 'activity')}'''

assert old_toggles in content, "old_toggles not found in App.tsx"
content = content.replace(old_toggles, new_toggles)

# 3. MessageView activity trigger
old_open_activity = '''                      onOpenActivity={(msgId) => {
                        setActiveActivityMessageId(msgId);
                        setIsActivityDrawerOpen(true);
                        setIsVisionDrawerOpen(false);
                        setIsArtifactDrawerOpen(false);
                      }}'''

new_open_activity = '''                      onOpenActivity={(msgId) => {
                        setActiveActivityMessageId(msgId);
                        setActiveDrawer('activity');
                      }}'''

assert old_open_activity in content, "old_open_activity not found in App.tsx"
content = content.replace(old_open_activity, new_open_activity)

# 4. Drawer onClose handlers
content = content.replace(
    'onClose={() => setIsArtifactDrawerOpen(false)}',
    'onClose={() => setActiveDrawer(\'none\')}'
)
content = content.replace(
    'onClose={() => setIsVisionDrawerOpen(false)}',
    'onClose={() => setActiveDrawer(\'none\')}'
)
content = content.replace(
    'onClose={() => setIsActivityDrawerOpen(false)}',
    'onClose={() => setActiveDrawer(\'none\')}'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated client/src/App.tsx with unified activeDrawer state machine successfully!")
