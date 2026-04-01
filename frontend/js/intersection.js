/**
 * Realistic Intersection Animation with Individual Vehicles
 * - Vehicle icons (cars, trucks, buses, motorcycles)
 * - Two-way traffic (right lane per direction)
 * - Following distance behavior
 * - Emergency vehicles with red icons
 * - Stop on yellow/red lights
 */

class Vehicle {
    constructor(id, type, lane, isEmergency = false) {
        this.id = id;
        this.type = type; // 'car', 'truck', 'bus', 'motorcycle'
        this.lane = lane; // 'N', 'S', 'E', 'W'
        this.isEmergency = isEmergency;

        // Position and movement
        this.x = 0;
        this.y = 0;
        this.speed = 0;
        this.maxSpeed = isEmergency ? 3.5 : 2.5;
        this.acceleration = 0.1;
        this.braking = 0.3;

        // Following distance
        this.minDistance = type === 'motorcycle' ? 25 : type === 'bus' ? 50 : 35;
        this.vehicleAhead = null;

        // Lane position (0 = right lane, 1 = left lane for opposite direction)
        this.laneOffset = 0;

        // SVG element
        this.element = null;

        this.initialize();
    }

    initialize() {
        // Create SVG group for this vehicle
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('id', this.id);

        // Set initial position
        const startPos = this.getStartPosition();
        this.x = startPos.x;
        this.y = startPos.y;

        // Draw the vehicle
        this.drawVehicle(g);

        this.element = g;
        document.getElementById('vehicles-layer').appendChild(g);
    }

    drawVehicle(g) {
        const isVertical = this.lane === 'N' || this.lane === 'S';

        if (this.isEmergency) {
            // Emergency vehicle - red with flashing lights
            this.drawEmergencyVehicle(g, isVertical);
        } else {
            switch (this.type) {
                case 'car':
                    this.drawCar(g, isVertical);
                    break;
                case 'truck':
                    this.drawTruck(g, isVertical);
                    break;
                case 'bus':
                    this.drawBus(g, isVertical);
                    break;
                case 'motorcycle':
                    this.drawMotorcycle(g, isVertical);
                    break;
            }
        }
    }

    drawCar(g, isVertical) {
        const color = this.getLaneColor();
        if (isVertical) {
            // Body
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', '-10');
            rect.setAttribute('y', '-20');
            rect.setAttribute('width', '20');
            rect.setAttribute('height', '40');
            rect.setAttribute('fill', color);
            rect.setAttribute('stroke', '#fff');
            rect.setAttribute('stroke-width', '1');
            rect.setAttribute('rx', '3');
            g.appendChild(rect);

            // Windshield
            const windshield = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            windshield.setAttribute('x', '-7');
            windshield.setAttribute('y', '-12');
            windshield.setAttribute('width', '14');
            windshield.setAttribute('height', '10');
            windshield.setAttribute('fill', '#4a5568');
            g.appendChild(windshield);
        } else {
            // Horizontal orientation
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', '-20');
            rect.setAttribute('y', '-10');
            rect.setAttribute('width', '40');
            rect.setAttribute('height', '20');
            rect.setAttribute('fill', color);
            rect.setAttribute('stroke', '#fff');
            rect.setAttribute('stroke-width', '1');
            rect.setAttribute('rx', '3');
            g.appendChild(rect);

            const windshield = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            windshield.setAttribute('x', '-12');
            windshield.setAttribute('y', '-7');
            windshield.setAttribute('width', '10');
            windshield.setAttribute('height', '14');
            windshield.setAttribute('fill', '#4a5568');
            g.appendChild(windshield);
        }
    }

    drawTruck(g, isVertical) {
        const color = this.getLaneColor();
        if (isVertical) {
            // Cargo
            const cargo = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            cargo.setAttribute('x', '-12');
            cargo.setAttribute('y', '-28');
            cargo.setAttribute('width', '24');
            cargo.setAttribute('height', '36');
            cargo.setAttribute('fill', color);
            cargo.setAttribute('stroke', '#fff');
            cargo.setAttribute('stroke-width', '1');
            g.appendChild(cargo);

            // Cabin
            const cabin = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            cabin.setAttribute('x', '-10');
            cabin.setAttribute('y', '8');
            cabin.setAttribute('width', '20');
            cabin.setAttribute('height', '18');
            cabin.setAttribute('fill', color);
            cabin.setAttribute('stroke', '#fff');
            cabin.setAttribute('stroke-width', '1');
            g.appendChild(cabin);
        } else {
            const cargo = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            cargo.setAttribute('x', '-28');
            cargo.setAttribute('y', '-12');
            cargo.setAttribute('width', '36');
            cargo.setAttribute('height', '24');
            cargo.setAttribute('fill', color);
            cargo.setAttribute('stroke', '#fff');
            cargo.setAttribute('stroke-width', '1');
            g.appendChild(cargo);

            const cabin = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            cabin.setAttribute('x', '8');
            cabin.setAttribute('y', '-10');
            cabin.setAttribute('width', '18');
            cabin.setAttribute('height', '20');
            cabin.setAttribute('fill', color);
            cabin.setAttribute('stroke', '#fff');
            cabin.setAttribute('stroke-width', '1');
            g.appendChild(cabin);
        }
    }

    drawBus(g, isVertical) {
        const color = this.getLaneColor();
        if (isVertical) {
            const body = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            body.setAttribute('x', '-14');
            body.setAttribute('y', '-32');
            body.setAttribute('width', '28');
            body.setAttribute('height', '64');
            body.setAttribute('fill', color);
            body.setAttribute('stroke', '#fff');
            body.setAttribute('stroke-width', '1');
            body.setAttribute('rx', '4');
            g.appendChild(body);

            // Windows
            for (let i = 0; i < 3; i++) {
                const win = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                win.setAttribute('x', '-10');
                win.setAttribute('y', -24 + i * 18);
                win.setAttribute('width', '20');
                win.setAttribute('height', '12');
                win.setAttribute('fill', '#4a5568');
                g.appendChild(win);
            }
        } else {
            const body = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            body.setAttribute('x', '-32');
            body.setAttribute('y', '-14');
            body.setAttribute('width', '64');
            body.setAttribute('height', '28');
            body.setAttribute('fill', color);
            body.setAttribute('stroke', '#fff');
            body.setAttribute('stroke-width', '1');
            body.setAttribute('rx', '4');
            g.appendChild(body);

            for (let i = 0; i < 3; i++) {
                const win = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                win.setAttribute('x', -24 + i * 18);
                win.setAttribute('y', '-10');
                win.setAttribute('width', '12');
                win.setAttribute('height', '20');
                win.setAttribute('fill', '#4a5568');
                g.appendChild(win);
            }
        }
    }

    drawMotorcycle(g, isVertical) {
        const color = this.getLaneColor();
        if (isVertical) {
            const body = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            body.setAttribute('x', '-6');
            body.setAttribute('y', '-12');
            body.setAttribute('width', '12');
            body.setAttribute('height', '24');
            body.setAttribute('fill', color);
            body.setAttribute('stroke', '#fff');
            body.setAttribute('stroke-width', '1');
            body.setAttribute('rx', '2');
            g.appendChild(body);
        } else {
            const body = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            body.setAttribute('x', '-12');
            body.setAttribute('y', '-6');
            body.setAttribute('width', '24');
            body.setAttribute('height', '12');
            body.setAttribute('fill', color);
            body.setAttribute('stroke', '#fff');
            body.setAttribute('stroke-width', '1');
            body.setAttribute('rx', '2');
            g.appendChild(body);
        }
    }

    drawEmergencyVehicle(g, isVertical) {
        // Red emergency vehicle with flashing light
        if (isVertical) {
            const body = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            body.setAttribute('x', '-12');
            body.setAttribute('y', '-24');
            body.setAttribute('width', '24');
            body.setAttribute('height', '48');
            body.setAttribute('fill', '#ef4444');
            body.setAttribute('stroke', '#fff');
            body.setAttribute('stroke-width', '2');
            body.setAttribute('rx', '3');
            g.appendChild(body);

            // Flashing light on top
            const light = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            light.setAttribute('cx', '0');
            light.setAttribute('cy', '-28');
            light.setAttribute('r', '4');
            light.setAttribute('fill', '#fef08a');
            light.setAttribute('class', 'emergency-light');
            g.appendChild(light);

            // Add text
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', '0');
            text.setAttribute('y', '2');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', '#fff');
            text.setAttribute('font-size', '10');
            text.setAttribute('font-weight', 'bold');
            text.textContent = '🚨';
            g.appendChild(text);
        } else {
            const body = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            body.setAttribute('x', '-24');
            body.setAttribute('y', '-12');
            body.setAttribute('width', '48');
            body.setAttribute('height', '24');
            body.setAttribute('fill', '#ef4444');
            body.setAttribute('stroke', '#fff');
            body.setAttribute('stroke-width', '2');
            body.setAttribute('rx', '3');
            g.appendChild(body);

            const light = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            light.setAttribute('cx', '-28');
            light.setAttribute('cy', '0');
            light.setAttribute('r', '4');
            light.setAttribute('fill', '#fef08a');
            light.setAttribute('class', 'emergency-light');
            g.appendChild(light);

            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', '0');
            text.setAttribute('y', '4');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', '#fff');
            text.setAttribute('font-size', '10');
            text.setAttribute('font-weight', 'bold');
            text.textContent = '🚨';
            g.appendChild(text);
        }
    }

    getLaneColor() {
        const colors = {
            'N': '#06b6d4',
            'S': '#10b981',
            'E': '#f59e0b',
            'W': '#8b5cf6'
        };
        return colors[this.lane] || '#06b6d4';
    }

    getStartPosition() {
        // Right lane positioning (vehicles travel on right side)
        const laneWidth = 40; // Distance from center

        switch (this.lane) {
            case 'N': // Coming from north, traveling south, right lane
                return { x: 400 - laneWidth, y: 50 };
            case 'S': // Coming from south, traveling north, right lane
                return { x: 400 + laneWidth, y: 750 };
            case 'E': // Coming from east, traveling west, right lane
                return { x: 750, y: 400 + laneWidth };
            case 'W': // Coming from west, traveling east, right lane
                return { x: 50, y: 400 - laneWidth };
            default:
                return { x: 400, y: 50 };
        }
    }

    update(phase, vehicles) {
        // Find vehicle ahead
        this.vehicleAhead = this.findVehicleAhead(vehicles);

        // Determine if should stop
        const shouldStop = this.shouldStopAtLight(phase);
        const distanceToStopLine = this.getDistanceToStopLine();
        const distanceToVehicleAhead = this.getDistanceToVehicleAhead();

        // Speed control
        if (shouldStop && distanceToStopLine < 100 && distanceToStopLine > 0) {
            // Approaching red/yellow light - brake
            if (this.speed > 0) {
                this.speed = Math.max(0, this.speed - this.braking);
            }
        } else if (distanceToVehicleAhead !== null && distanceToVehicleAhead < this.minDistance) {
            // Too close to vehicle ahead - brake
            if (this.speed > 0) {
                this.speed = Math.max(0, this.speed - this.braking);
            }
        } else {
            // Accelerate to max speed
            if (this.speed < this.maxSpeed) {
                this.speed = Math.min(this.maxSpeed, this.speed + this.acceleration);
            }
        }

        // Move vehicle
        this.move();

        // Update SVG position
        if (this.element) {
            this.element.setAttribute('transform', `translate(${this.x}, ${this.y})`);
        }
    }

    shouldStopAtLight(phase) {
        // Emergency vehicles ignore lights
        if (this.isEmergency) return false;

        // Stop on red or yellow
        return phase === 'red' || phase === 'yellow';
    }

    getDistanceToStopLine() {
        const stopLine = 280; // Distance from center where stop line is

        switch (this.lane) {
            case 'N':
                return 400 - stopLine - this.y;
            case 'S':
                return this.y - (400 + stopLine);
            case 'E':
                return this.x - (400 + stopLine);
            case 'W':
                return 400 - stopLine - this.x;
            default:
                return 1000;
        }
    }

    findVehicleAhead(vehicles) {
        const sameLaneVehicles = vehicles.filter(v =>
            v.lane === this.lane && v.id !== this.id
        );

        let closest = null;
        let minDist = Infinity;

        for (const v of sameLaneVehicles) {
            const dist = this.getDistanceTo(v);
            if (dist > 0 && dist < minDist) {
                minDist = dist;
                closest = v;
            }
        }

        return closest;
    }

    getDistanceTo(vehicle) {
        switch (this.lane) {
            case 'N':
                return vehicle.y - this.y;
            case 'S':
                return this.y - vehicle.y;
            case 'E':
                return this.x - vehicle.x;
            case 'W':
                return vehicle.x - this.x;
            default:
                return 0;
        }
    }

    getDistanceToVehicleAhead() {
        if (!this.vehicleAhead) return null;
        return this.getDistanceTo(this.vehicleAhead);
    }

    move() {
        switch (this.lane) {
            case 'N':
                this.y += this.speed;
                break;
            case 'S':
                this.y -= this.speed;
                break;
            case 'E':
                this.x -= this.speed;
                break;
            case 'W':
                this.x += this.speed;
                break;
        }
    }

    isOffScreen() {
        return this.x < -50 || this.x > 850 || this.y < -50 || this.y > 850;
    }

    remove() {
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
    }
}

class IntersectionAnimator {
    constructor() {
        this.vehicles = [];
        this.nextVehicleId = 0;
        this.animationFrame = null;
        this.lanePhases = { N: 'red', S: 'red', E: 'red', W: 'red' };
        this.emergencyActive = false;

        this.startAnimation();
    }

    updateSignals(lanes) {
        const colorMap = {
            'green': '#10b981',
            'yellow': '#f59e0b',
            'red': '#ef4444'
        };

        ['N', 'S', 'E', 'W'].forEach(lane => {
            const light = document.getElementById(`light-${lane}`);
            const timerBg = document.getElementById(`timer-bg-${lane}`);
            const timerText = document.getElementById(`timer-${lane}`);
            const countText = document.getElementById(`count-${lane}`);

            if (light && lanes[lane]) {
                const phase = lanes[lane].phase;
                const remaining = lanes[lane].remaining || 0;
                const vehicles = lanes[lane].vehicles || 0;
                const color = colorMap[phase] || colorMap['red'];

                // Store phase for vehicle updates
                this.lanePhases[lane] = phase;

                // Update light
                light.setAttribute('fill', color);

                // Update timer
                if (timerBg) {
                    const bgColor = phase === 'green' ? 'rgba(16, 185, 129, 0.2)' :
                                   phase === 'yellow' ? 'rgba(245, 158, 11, 0.2)' :
                                   'rgba(239, 68, 68, 0.2)';
                    timerBg.setAttribute('fill', bgColor);
                    timerBg.setAttribute('stroke', color);
                }

                if (timerText) {
                    timerText.textContent = remaining;
                }

                if (countText) {
                    countText.textContent = `${vehicles} vehicle${vehicles !== 1 ? 's' : ''}`;
                }

                // Glow effect
                if (phase === 'green') {
                    light.style.filter = 'drop-shadow(0 0 10px #10b981)';
                } else {
                    light.style.filter = 'none';
                }
            }
        });
    }

    updateVehicles(lanes) {
        const targetCounts = {};
        ['N', 'S', 'E', 'W'].forEach(lane => {
            targetCounts[lane] = Math.min(lanes[lane]?.vehicles || 0, 15); // Max 15 per lane for better visibility
        });

        // Remove excess vehicles
        ['N', 'S', 'E', 'W'].forEach(lane => {
            const laneVehicles = this.vehicles.filter(v => v.lane === lane);
            const excess = laneVehicles.length - targetCounts[lane];

            if (excess > 0) {
                // Remove furthest vehicles
                const toRemove = laneVehicles
                    .sort((a, b) => this.getVehicleProgress(b) - this.getVehicleProgress(a))
                    .slice(0, excess);

                toRemove.forEach(v => {
                    v.remove();
                    const idx = this.vehicles.indexOf(v);
                    if (idx > -1) this.vehicles.splice(idx, 1);
                });
            }
        });

        // Add missing vehicles
        ['N', 'S', 'E', 'W'].forEach(lane => {
            const laneVehicles = this.vehicles.filter(v => v.lane === lane);
            const needed = targetCounts[lane] - laneVehicles.length;

            for (let i = 0; i < needed; i++) {
                this.spawnVehicle(lane);
            }
        });
    }

    getVehicleProgress(vehicle) {
        // How far the vehicle has traveled
        switch (vehicle.lane) {
            case 'N': return vehicle.y;
            case 'S': return 800 - vehicle.y;
            case 'E': return 800 - vehicle.x;
            case 'W': return vehicle.x;
            default: return 0;
        }
    }

    spawnVehicle(lane, isEmergency = false) {
        const types = ['car', 'car', 'car', 'truck', 'bus', 'motorcycle'];
        const type = types[Math.floor(Math.random() * types.length)];

        const vehicle = new Vehicle(`vehicle-${this.nextVehicleId++}`, type, lane, isEmergency);
        this.vehicles.push(vehicle);
    }

    startAnimation() {
        const animate = () => {
            // Update all vehicles
            this.vehicles.forEach(vehicle => {
                const phase = this.lanePhases[vehicle.lane] || 'red';
                vehicle.update(phase, this.vehicles);
            });

            // Remove off-screen vehicles
            this.vehicles = this.vehicles.filter(vehicle => {
                if (vehicle.isOffScreen()) {
                    vehicle.remove();
                    return false;
                }
                return true;
            });

            this.animationFrame = requestAnimationFrame(animate);
        };

        animate();
    }

    stopAnimation() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    }

    clearVehicles() {
        this.vehicles.forEach(v => v.remove());
        this.vehicles = [];
    }
}

// CSS for emergency light animation
const style = document.createElement('style');
style.textContent = `
    @keyframes emergency-flash {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    .emergency-light {
        animation: emergency-flash 0.5s infinite;
    }
`;
document.head.appendChild(style);

// Create global instance
const intersectionAnimator = new IntersectionAnimator();
