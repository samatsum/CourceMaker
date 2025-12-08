// docker compose stop
// docker compose rm -f
// docker compose up -d --build
//http://localhost:5173/にアクセス！！！！
// src/App.jsx
import { useState, useMemo } from 'react';
import './App.css';

function App() {
  // === 設定値 ===
  const COURSE_WIDTH = 1000;
  const COURSE_HEIGHT = 546;
  
  // 左側のパーツ置き場（パレット）の幅
  const PALETTE_WIDTH = 200;
  // パレットエリアの3分割高さ
  const PALETTE_SECTION_HEIGHT = COURSE_HEIGHT / 3;

  // SVG全体の定義
  const VIEWBOX_X = -PALETTE_WIDTH;
  const VIEWBOX_WIDTH = COURSE_WIDTH + PALETTE_WIDTH;

  const NUM_DIVISIONS = 6;
  const DIVISION_SIZE = 546 / NUM_DIVISIONS; 

  //レーンの太さ！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！本来は1.5cmだけど、見やすさ優先で15cmにしている！！！！！！！！！！！！！！！！！！！！！！！！！！！！！！
  const PART_TYPES = {
    yellow: { length: 120, color: '#FFD700', width: 15, label: '長 (120cm)' },
    blue:   { length: 60,  color: '#4169E1', width: 15, label: '中 (60cm)' },
    green:  { length: 42,  color: '#32CD32', width: 15, label: '短 (42cm)' },
  };

  // === 状態管理 ===
  const [parts, setParts] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [isDeleteMode, setIsDeleteMode] = useState(false); 
  const [collidingId, setCollidingId] = useState(null);

  // === 個数カウント ===
  const formatCount = (num) => String(num).padStart(2, '0');
  
  const counts = {
    yellow: parts.filter(p => p.type === 'yellow').length,
    blue: parts.filter(p => p.type === 'blue').length,
    green: parts.filter(p => p.type === 'green').length,
  };

  // === 衝突判定ロジック (SAT) ===
  const toRadians = (degrees) => degrees * (Math.PI / 180);

  const getCorners = (part) => {
    const def = PART_TYPES[part.type];
    const rad = toRadians(part.rotation);
    const hw = def.width / 2;
    const hl = def.length / 2;

    const cornersLocal = [
      { x: -hl, y: -hw },
      { x: hl, y: -hw },
      { x: hl, y: hw },
      { x: -hl, y: hw }
    ];

    return cornersLocal.map(p => ({
      x: part.x + (p.x * Math.cos(rad) - p.y * Math.sin(rad)),
      y: part.y + (p.x * Math.sin(rad) + p.y * Math.cos(rad))
    }));
  };

  const dot = (v1, v2) => v1.x * v2.x + v1.y * v2.y;

  const project = (corners, axis) => {
    let min = dot(corners[0], axis);
    let max = min;
    for (let i = 1; i < corners.length; i++) {
      const p = dot(corners[i], axis);
      if (p < min) min = p;
      if (p > max) max = p;
    }
    return { min, max };
  };

  const checkCollisionSAT = (p1, p2) => {
    const corners1 = getCorners(p1);
    const corners2 = getCorners(p2);

    const axes = [];
    for (let i = 0; i < corners1.length; i++) {
      const p1_pt = corners1[i];
      const p2_pt = corners1[(i + 1) % corners1.length];
      const edge = { x: p1_pt.x - p2_pt.x, y: p1_pt.y - p2_pt.y };
      axes.push({ x: -edge.y, y: edge.x });
    }
    for (let i = 0; i < corners2.length; i++) {
      const p1_pt = corners2[i];
      const p2_pt = corners2[(i + 1) % corners2.length];
      const edge = { x: p1_pt.x - p2_pt.x, y: p1_pt.y - p2_pt.y };
      axes.push({ x: -edge.y, y: edge.x });
    }

    for (const axis of axes) {
      const proj1 = project(corners1, axis);
      const proj2 = project(corners2, axis);
      if (proj1.max < proj2.min || proj2.max < proj1.min) return false;
    }
    return true;
  };

  const getCollisionId = useMemo(() => {
    return (currentPart) => {
      if (!currentPart || isDeleteMode) return null;
      if (currentPart.x < 0) return null; 

      for (const otherPart of parts) {
        if (currentPart.id !== otherPart.id) {
          if (otherPart.locked) { 
            if (checkCollisionSAT(currentPart, otherPart)) {
              return otherPart.id;
            }
          }
        }
      }
      return null;
    };
  }, [parts, isDeleteMode]);

  // === 画像保存機能 ===
  const downloadJpeg = () => {
    setSelectedId(null);
    setIsDeleteMode(false);

    setTimeout(() => {
        const svgElement = document.getElementById('course-svg');
        if (!svgElement) return;

        const serializer = new XMLSerializer();
        let svgString = serializer.serializeToString(svgElement);

        const targetViewBox = `viewBox="0 0 ${COURSE_WIDTH} ${COURSE_HEIGHT}"`;
        svgString = svgString.replace(/viewBox="[^"]*"/, targetViewBox);

        const canvas = document.createElement('canvas');
        canvas.width = COURSE_WIDTH;
        canvas.height = COURSE_HEIGHT;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const img = new Image();
        const svgBlob = new Blob([svgString], {type: 'image/svg+xml;charset=utf-8'});
        const url = URL.createObjectURL(svgBlob);

        img.onload = () => {
            ctx.drawImage(img, 0, 0, COURSE_WIDTH, COURSE_HEIGHT);
            
            const now = new Date();
            const yyyy = now.getFullYear();
            const mm = String(now.getMonth() + 1).padStart(2, '0');
            const dd = String(now.getDate()).padStart(2, '0');
            const hh = String(now.getHours()).padStart(2, '0');
            const min = String(now.getMinutes()).padStart(2, '0');
            const ss = String(now.getSeconds()).padStart(2, '0');
            
            const filename = `CourseImage_${yyyy}${mm}${dd}_${hh}${mm}${ss}.jpg`;

            const a = document.createElement('a');
            a.download = filename;
            a.href = canvas.toDataURL('image/jpeg', 0.9);
            a.click();
            
            URL.revokeObjectURL(url);
        };
        img.src = url;
    }, 100);
  };

  // === パーツ操作ロジック ===
  
  const addPart = (typeKey) => {
    if (isDeleteMode) setIsDeleteMode(false); 

    let baseY = 0;
    if (typeKey === 'yellow') baseY = PALETTE_SECTION_HEIGHT * 0.5;
    else if (typeKey === 'blue') baseY = PALETTE_SECTION_HEIGHT * 1.5;
    else if (typeKey === 'green') baseY = PALETTE_SECTION_HEIGHT * 2.5;

    const randomOffset = (Math.random() - 0.5) * 40;

    const newPart = {
      id: Date.now(),
      type: typeKey,
      x: -PALETTE_WIDTH / 2,  
      y: baseY + randomOffset, 
      rotation: 0,
      locked: false,
    };
    
    setParts([...parts, newPart]);
    setSelectedId(newPart.id);
    setCollidingId(null);
  };

  const copySelected = () => {
    if (isDeleteMode) setIsDeleteMode(false); 
    
    const selectedPart = parts.find(p => p.id === selectedId);
    if (selectedPart) {
      const OFFSET = 20; 
      const newPart = {
        ...selectedPart,
        id: Date.now() + 1,
        x: selectedPart.x + OFFSET, 
        y: selectedPart.y + OFFSET,
        locked: false,
      };
      
      if (getCollisionId(newPart)) {
          alert("コピー先の位置が固定されたパーツと重なるため、コピーできません。");
          return;
      }
      
      setParts([...parts, newPart]);
      setSelectedId(newPart.id);
    }
  };

  const deleteSelected = () => {
    const target = parts.find(p => p.id === selectedId);
    if (target && target.locked) return; 

    setParts(parts.filter(p => p.id !== selectedId));
    setSelectedId(null);
    setCollidingId(null);
  };
  
  const deleteClicked = (id) => {
    const target = parts.find(p => p.id === id);
    if (isDeleteMode && target && !target.locked) {
      setParts(parts.filter(p => p.id !== id));
      setSelectedId(null);
      setCollidingId(null);
    }
  };

  const rotateSelected = (angle) => {
    if (isDeleteMode) setIsDeleteMode(false); 
    
    setParts(parts.map(p => {
      if (p.id === selectedId && !p.locked) {
        let newRotation = (p.rotation + angle) % 360;
        if (newRotation < 0) newRotation += 360;
        
        const rotatedPart = { ...p, rotation: newRotation };
        
        if (getCollisionId(rotatedPart)) {
             alert("回転させると固定されたパーツと重なるため、回転できません。");
             return p;
        }

        return rotatedPart;
      }
      return p;
    }));
    setCollidingId(null);
  };

  const toggleLock = () => {
    if (isDeleteMode) setIsDeleteMode(false); 
    
    setParts(parts.map(p => {
      if (p.id === selectedId) {
        return { ...p, locked: !p.locked };
      }
      return p;
    }));
    setCollidingId(null);
  };
  
  const toggleDeleteMode = () => {
      setIsDeleteMode(!isDeleteMode);
      setSelectedId(null);
      setCollidingId(null);
  };

  // === ドラッグ操作ロジック ===

  const [isDragging, setIsDragging] = useState(false);
  const [dragStartPos, setDragStartPos] = useState({ x: 0, y: 0 });
  const [partStartPos, setPartStartPos] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e, part) => {
    if (isDeleteMode) {
      deleteClicked(part.id);
      return;
    }

    if (e.buttons === 1) { 
        e.stopPropagation();
        setSelectedId(part.id);

        if (!part.locked) {
          setIsDragging(true);
          setDragStartPos({ x: e.clientX, y: e.clientY });
          setPartStartPos({ x: part.x, y: part.y });
          setCollidingId(null);
        }
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging && selectedId) {
      e.preventDefault();
      e.stopPropagation();

      const svgElement = document.getElementById('course-svg');
      let scale = 1;
      if (svgElement) {
        const rect = svgElement.getBoundingClientRect();
        scale = VIEWBOX_WIDTH / rect.width; 
      }

      const dx = (e.clientX - dragStartPos.x) * scale;
      const dy = (e.clientY - dragStartPos.y) * scale;

      const updatedParts = parts.map(p => {
        if (p.id === selectedId) {
          const newPart = {
            ...p,
            x: partStartPos.x + dx,
            y: partStartPos.y + dy
          };
          
          const collisionId = getCollisionId(newPart);
          
          if (collisionId) {
            setCollidingId(collisionId);
            return p; 
          } else {
            setCollidingId(null);
            return newPart;
          }
        }
        return p;
      });

      setParts(updatedParts);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setCollidingId(null);
  };

  const selectedPart = parts.find(p => p.id === selectedId);
  
  const orderedParts = [...parts].sort((a, b) => {
    if (a.id === selectedId) return 1;
    if (b.id === selectedId) return -1;
    return 0;
  });

  return (
    <div className="app" onMouseMove={handleMouseMove} onMouseUp={handleMouseUp}>
      <h1>コースレイアウト作成 (v1.2)</h1>

      <div style={{marginBottom: '10px', textAlign: 'center'}}>
        <button 
            onClick={downloadJpeg}
            style={{backgroundColor: '#FF4444', color: 'white', fontWeight: 'bold', fontSize: '0.9rem', padding: '6px 20px'}}
            title="コース部分だけを画像として保存します"
        >
            📷 コース図保存 (.jpg)
        </button>
      </div>
      
      <div className="controls">
        <div style={{display:'flex', gap:'8px'}}>
            <button onClick={() => addPart('yellow')} style={{backgroundColor: '#FFFACD'}}>
              ＋黄 ({formatCount(counts.yellow)})
            </button>
            <button onClick={() => addPart('blue')} style={{backgroundColor: '#ADD8E6'}}>
              ＋青 ({formatCount(counts.blue)})
            </button>
            <button onClick={() => addPart('green')} style={{backgroundColor: '#90EE90'}}>
              ＋緑 ({formatCount(counts.green)})
            </button>
        </div>

        <div style={{borderLeft:'1px solid #ccc', margin:'0 4px'}}></div>

        <button onClick={copySelected} disabled={!selectedId || isDeleteMode || collidingId}>コピペ</button>
        
        <button 
          onClick={toggleLock} 
          disabled={!selectedId || isDeleteMode}
          className={selectedPart?.locked ? 'active' : ''}
          title="移動や回転を禁止します"
        >
          {selectedPart?.locked ? '🔒 固定〇' : '🔓 固定×'}
        </button>

        <button 
          onClick={deleteSelected} 
          disabled={!selectedId || selectedPart?.locked || isDeleteMode} 
          style={{color: selectedPart?.locked ? '#aaa' : 'red'}}
        >
          削除
        </button>

        <div style={{borderLeft:'1px solid #ccc', margin:'0 4px'}}></div>

        <div style={{display:'flex', gap:'2px'}}>
            <button onClick={() => rotateSelected(1)} disabled={!selectedId || selectedPart?.locked || isDeleteMode || collidingId}>1°</button>
            <button onClick={() => rotateSelected(10)} disabled={!selectedId || selectedPart?.locked || isDeleteMode || collidingId}>10°</button>
            <button onClick={() => rotateSelected(45)} disabled={!selectedId || selectedPart?.locked || isDeleteMode || collidingId}>45°</button>
            <button onClick={() => rotateSelected(90)} disabled={!selectedId || selectedPart?.locked || isDeleteMode || collidingId}>90°</button>
        </div>

        <div style={{borderLeft:'1px solid #ccc', margin:'0 4px'}}></div>
        
        <button 
          onClick={toggleDeleteMode}
          className={isDeleteMode ? 'active' : ''}
          style={{fontWeight:'normal', color: isDeleteMode ? 'white' : 'red', backgroundColor: isDeleteMode ? 'red' : 'white'}}
        >
           削除モード: {isDeleteMode ? '〇' : '×'}
        </button>
      </div>

      <div className="canvas-wrapper">
        <svg 
          id="course-svg"
          viewBox={`${VIEWBOX_X} 0 ${VIEWBOX_WIDTH} ${COURSE_HEIGHT}`}
          style={{
            background: '#fff', 
            maxWidth: '98%', 
            maxHeight: '85vh',
            boxShadow: '0 0 10px rgba(0,0,0,0.2)',
            cursor: isDeleteMode ? 'crosshair' : (isDragging ? 'grabbing' : 'default')
          }}
          onClick={() => {
             if (!isDragging && !isDeleteMode) setSelectedId(null);
          }} 
        >
          {/* パレット背景エリア */}
          <rect x={-PALETTE_WIDTH} y={0} width={PALETTE_WIDTH} height={PALETTE_SECTION_HEIGHT} fill="#FFFFF0" />
          <rect x={-PALETTE_WIDTH} y={PALETTE_SECTION_HEIGHT} width={PALETTE_WIDTH} height={PALETTE_SECTION_HEIGHT} fill="#F0F8FF" />
          <rect x={-PALETTE_WIDTH} y={PALETTE_SECTION_HEIGHT * 2} width={PALETTE_WIDTH} height={PALETTE_SECTION_HEIGHT} fill="#F0FFF0" />

          {/* 境界線 */}
          <line x1="0" y1="0" x2="0" y2={COURSE_HEIGHT} stroke="#999" strokeWidth="2" />
          <line x1={-PALETTE_WIDTH} y1={PALETTE_SECTION_HEIGHT} x2="0" y2={PALETTE_SECTION_HEIGHT} stroke="#ddd" strokeWidth="1" />
          <line x1={-PALETTE_WIDTH} y1={PALETTE_SECTION_HEIGHT * 2} x2="0" y2={PALETTE_SECTION_HEIGHT * 2} stroke="#ddd" strokeWidth="1" />
          
          <text x={-PALETTE_WIDTH/2} y={30} textAnchor="middle" fill="#B8860B" fontSize="14" fontWeight="bold">黄色置き場</text>
          <text x={-PALETTE_WIDTH/2} y={PALETTE_SECTION_HEIGHT + 30} textAnchor="middle" fill="#4682B4" fontSize="14" fontWeight="bold">青色置き場</text>
          <text x={-PALETTE_WIDTH/2} y={PALETTE_SECTION_HEIGHT * 2 + 30} textAnchor="middle" fill="#2E8B57" fontSize="14" fontWeight="bold">緑色置き場</text>

          <defs>
            <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
              <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#e0e0e0" strokeWidth="1"/>
            </pattern>
          </defs>
          
          <rect x="0" y="0" width={COURSE_WIDTH} height={COURSE_HEIGHT} fill="url(#grid)" />

          {[...Array(NUM_DIVISIONS - 1)].map((_, i) => (
             <line 
               key={`div-h-${i}`}
               x1={0}
               y1={(i + 1) * DIVISION_SIZE}
               x2={COURSE_WIDTH}
               y2={(i + 1) * DIVISION_SIZE}
               stroke="purple"
               strokeWidth="1"
               strokeDasharray="4"
             />
          ))}

          {orderedParts.map(part => {
            const def = PART_TYPES[part.type];
            const isSelected = part.id === selectedId;
            const isColliding = part.id === collidingId;
            const deleteHighlight = isDeleteMode && !part.locked;
            
            const rotationTransform = `rotate(${part.rotation}, 0, 0)`;

            return (
              <g 
                key={part.id}
                transform={`translate(${part.x}, ${part.y})`}
                onMouseDown={(e) => handleMouseDown(e, part)}
                onClick={(e) => e.stopPropagation()}
                style={{
                    cursor: part.locked ? 'not-allowed' : (isDeleteMode ? 'pointer' : 'grab'),
                    opacity: part.locked ? 0.8 : 1
                }}
              >
                <rect 
                  x={-def.length / 2} 
                  y={-def.width / 2} 
                  width={def.length} 
                  height={def.width} 
                  fill={def.color} 
                  className={`${isSelected ? 'selected' : ''} ${part.locked ? 'locked' : ''}`}
                  stroke={isColliding || deleteHighlight ? 'red' : 'none'}
                  strokeWidth={isColliding || deleteHighlight ? 4 : 0}
                  transform={rotationTransform} 
                />
                
                <circle cx="0" cy="0" r="3" fill="black" opacity="0.5" />
                
                {part.locked && isSelected && (
                    <text x={0} y={-10} textAnchor="middle" fontSize="10" fill="#333" transform={rotationTransform}>🔒</text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

export default App;
