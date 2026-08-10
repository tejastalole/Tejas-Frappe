/* Gym Management PWA */
(function () {
	const API = "/api/method";
	const state = {
		user: null,
		config: null,
		view: "home",
		members: [],
		memberDetail: null,
	};

	const $ = (sel) => document.querySelector(sel);
	const loginScreen = $("#screen-login");
	const appScreen = $("#screen-app");
	const main = $("#main-content");
	const toast = $("#toast");

	function showToast(msg, type = "") {
		toast.textContent = msg;
		toast.className = `toast ${type}`;
		toast.classList.remove("hidden");
		setTimeout(() => toast.classList.add("hidden"), 3200);
	}

	async function api(method, args = {}) {
		const res = await fetch(`${API}/${method}`, {
			method: "POST",
			credentials: "include",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.gym_pwa.csrf_token,
			},
			body: JSON.stringify(args),
		});
		const data = await res.json();
		if (data.exc || data._server_messages) {
			let msg = "Request failed";
			try {
				const msgs = JSON.parse(data._server_messages || "[]");
				if (msgs[0]) msg = JSON.parse(msgs[0]).message || msg;
			} catch (e) {
				/* ignore */
			}
			if (data.message && typeof data.message === "string") msg = data.message;
			throw new Error(msg);
		}
		return data.message;
	}

	function getLocation() {
		return new Promise((resolve) => {
			if (!navigator.geolocation) return resolve(null);
			navigator.geolocation.getCurrentPosition(
				(pos) =>
					resolve({
						latitude: pos.coords.latitude,
						longitude: pos.coords.longitude,
					}),
				() => resolve(null),
				{ enableHighAccuracy: true, timeout: 12000 }
			);
		});
	}

	function initials(name) {
		return (name || "?")
			.split(" ")
			.map((w) => w[0])
			.join("")
			.slice(0, 2)
			.toUpperCase();
	}

	function memberAvatar(m) {
		if (m.image) {
			return `<img src="${m.image}" alt="" />`;
		}
		return initials(m.member_name);
	}

	function val(v, fallback = "—") {
		return v !== null && v !== undefined && String(v).trim() !== "" ? v : fallback;
	}

	function formatMoney(amount) {
		if (amount === null || amount === undefined || amount === "") return "—";
		return `₹ ${Number(amount).toLocaleString("en-IN")}`;
	}

	function parseTimeToMinutes(t) {
		if (!t) return null;
		const parts = String(t).split(/[:.]/).map((p) => parseInt(p, 10) || 0);
		return parts[0] * 60 + (parts[1] || 0);
	}

	function formatTime(t) {
		if (!t || String(t).trim() === "") return "—";
		const raw = String(t).trim();
		const parts = raw.split(/[:.]/);
		let h = parseInt(parts[0], 10);
		if (Number.isNaN(h)) return raw;
		const m = String(parts[1] || 0).padStart(2, "0");
		const ampm = h >= 12 ? "PM" : "AM";
		h = h % 12 || 12;
		return `${h}:${m} ${ampm}`;
	}

	function formatDuration(checkIn, checkOut) {
		const start = parseTimeToMinutes(checkIn);
		const end = parseTimeToMinutes(checkOut);
		if (start === null || end === null || end < start) return null;
		const mins = end - start;
		const h = Math.floor(mins / 60);
		const m = mins % 60;
		if (h && m) return `${h}h ${m}m`;
		if (h) return `${h}h`;
		return `${m}m`;
	}

	function attendanceTimesHtml(a) {
		const checkIn = formatTime(a.check_in_time);
		const checkOut = a.check_out_time ? formatTime(a.check_out_time) : null;
		const duration = checkOut ? formatDuration(a.check_in_time, a.check_out_time) : null;
		return `
			<div class="time-block">
				<div class="time-line">
					<span class="time-label">Check-in</span>
					<span class="time-value">${escapeHtml(checkIn)}</span>
				</div>
				${
					checkOut
						? `<div class="time-line">
					<span class="time-label">Check-out</span>
					<span class="time-value">${escapeHtml(checkOut)}</span>
				</div>`
						: `<div class="time-line"><span class="time-label">Check-out</span><span class="time-value muted">Not yet</span></div>`
				}
				${
					duration
						? `<div class="time-line"><span class="time-label">Duration</span><span class="time-value">${escapeHtml(duration)}</span></div>`
						: ""
				}
			</div>
		`;
	}

	function infoCard(title, rows) {
		const body = rows
			.filter((r) => r)
			.map(
				([label, value]) => `
			<div class="info-row">
				<span class="info-label">${escapeHtml(label)}</span>
				<span class="info-value">${value}</span>
			</div>
		`
			)
			.join("");
		if (!body) return "";
		return `
			<div class="info-card">
				<h3 class="info-card-title">${escapeHtml(title)}</h3>
				${body}
			</div>
		`;
	}

	function memberMetaLine(m) {
		const parts = [];
		if (m.plan_name) parts.push(`Plan: ${m.plan_name}`);
		if (m.trainer_name) parts.push(`Trainer: ${m.trainer_name}`);
		if (m.checked_in_today && m.today_check_in_time) {
			let t = `In: ${formatTime(m.today_check_in_time)}`;
			if (m.today_check_out_time) t += ` · Out: ${formatTime(m.today_check_out_time)}`;
			parts.push(t);
		}
		return parts.length ? `<p class="member-meta">${escapeHtml(parts.join(" · "))}</p>` : "";
	}

	async function login(usr, pwd) {
		const res = await fetch(`${API}/login`, {
			method: "POST",
			credentials: "include",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.gym_pwa.csrf_token,
			},
			body: JSON.stringify({ usr, pwd }),
		});
		const data = await res.json();
		if (data.message !== "Logged In" && data.exc) {
			throw new Error("Invalid login credentials");
		}
	}

	async function logout() {
		await fetch(`${API}/logout`, {
			method: "POST",
			credentials: "include",
			headers: { "X-Frappe-CSRF-Token": window.gym_pwa.csrf_token },
		});
		state.user = null;
		loginScreen.classList.add("active");
		appScreen.classList.remove("active");
	}

	function startLiveClock() {
		const el = $("#live-clock");
		if (!el) return;
		const tick = () => {
			const now = new Date();
			el.textContent = now.toLocaleTimeString("en-IN", {
				hour: "numeric",
				minute: "2-digit",
				hour12: true,
			});
		};
		tick();
		setInterval(tick, 30000);
	}

	function emptyState(icon, message) {
		return `<div class="empty-state"><div class="empty-icon">${icon}</div><p>${escapeHtml(message)}</p></div>`;
	}

	async function bootApp() {
		state.config = await api("gym_management.api.mobile.get_app_config");
		state.user = state.config.user;
		$("#gym-name").textContent = state.config.gym_name;
		loginScreen.classList.remove("active");
		appScreen.classList.add("active");
		registerServiceWorker();
		startLiveClock();
		showView("home");
	}

	async function renderHome() {
		$("#page-title").textContent = "Home";
		main.innerHTML = `<div class="loading">Loading…</div>`;
		const stats = await api("gym_management.api.mobile.get_dashboard");
		main.innerHTML = `
			<div class="stats">
				<div class="stat-card"><div class="stat-icon">👥</div><div class="value">${stats.active_members}</div><div class="label">Active Members</div></div>
				<div class="stat-card"><div class="stat-icon">✓</div><div class="value">${stats.today_attendance}</div><div class="label">Today's Check-ins</div></div>
				<div class="stat-card"><div class="stat-icon">📋</div><div class="value">${stats.active_memberships}</div><div class="label">Active Plans</div></div>
				<div class="stat-card"><div class="stat-icon">⏳</div><div class="value">${stats.expiring_soon}</div><div class="label">Expiring Soon</div></div>
			</div>
			<p class="section-title">Quick check-in / check-out</p>
			<div class="search-box"><input type="search" class="search-input" id="home-search" placeholder="Search name or mobile…" /></div>
			<div id="home-members" class="member-list"></div>
		`;
		const search = $("#home-search");
		const load = async () => {
			const list = await api("gym_management.api.mobile.get_members", {
				search: search.value,
				limit: 8,
			});
			$("#home-members").innerHTML =
				list.length === 0
					? emptyState("🔍", "No members found")
					: list.map((m) => memberRowHtml(m, true)).join("");
			bindMemberClicks("#home-members");
		};
		search.addEventListener("input", debounce(load, 350));
		await load();
	}

	function memberActionHtml(m, showActions) {
		if (!showActions) {
			if (m.checked_in_today && !m.today_check_out_time) {
				return `<span class="badge">${m.today_check_in_time ? formatTime(m.today_check_in_time) : "In"}</span>`;
			}
			if (m.today_check_out_time) {
				return `<span class="badge done">Done</span>`;
			}
			return `<span class="badge done">Active</span>`;
		}
		if (!m.checked_in_today) {
			return `<button type="button" class="btn btn-primary btn-sm" data-checkin="${m.name}">Check In</button>`;
		}
		if (m.today_check_out_time) {
			return `<span class="badge done">Done</span>`;
		}
		if (m.today_attendance_log) {
			return `<button type="button" class="btn btn-checkout btn-sm" data-checkout="${m.today_attendance_log}" data-member="${m.name}">Check Out</button>`;
		}
		return `<span class="badge">${m.today_check_in_time ? formatTime(m.today_check_in_time) : "In"}</span>`;
	}

	function memberRowHtml(m, showActions) {
		const action = memberActionHtml(m, showActions);
		return `
			<div class="member-card" data-member="${m.name}">
				<div class="avatar">${memberAvatar(m)}</div>
				<div class="member-info">
					<h3>${escapeHtml(m.member_name)}</h3>
					<p>${escapeHtml(m.mobile_no || m.name)}</p>
					${memberMetaLine(m)}
				</div>
				${action}
			</div>
		`;
	}

	async function renderMembers() {
		$("#page-title").textContent = "Members";
		main.innerHTML = `
			<div class="search-box"><input type="search" class="search-input" id="member-search" placeholder="Search members…" autofocus /></div>
			<div id="member-list" class="member-list"><div class="loading">Loading…</div></div>
		`;
		const search = $("#member-search");
		const load = async () => {
			state.members = await api("gym_management.api.mobile.get_members", {
				search: search.value,
			});
			$("#member-list").innerHTML = state.members.map((m) => memberRowHtml(m, false)).join("");
			bindMemberClicks("#member-list");
		};
		search.addEventListener("input", debounce(load, 350));
		await load();
	}

	async function renderAttendance() {
		$("#page-title").textContent = "Today";
		main.innerHTML = `<div class="loading">Loading…</div>`;
		const rows = await api("gym_management.api.mobile.get_today_attendance");
		if (!rows.length) {
			main.innerHTML = emptyState("📅", "No check-ins today yet");
			return;
		}
		main.innerHTML =
			`<p class="section-title">${rows.length} check-in(s) today</p>` +
			rows
				.map(
					(r) => `
				<div class="att-row">
					<strong>${escapeHtml(r.member_name)}</strong>
					${attendanceTimesHtml(r)}
				</div>
			`
				)
				.join("");
	}

	function membershipCard(ms) {
		if (!ms) {
			return infoCard("Membership Plan", [["Status", `<span class="status-pill warn">No active plan</span>`]]);
		}
		const plan = ms.plan || {};
		return infoCard("Membership Plan", [
			["Plan", `<strong>${escapeHtml(val(ms.membership_plan))}</strong>`],
			["Status", `<span class="status-pill ${ms.status === "Active" ? "ok" : ""}">${escapeHtml(val(ms.status))}</span>`],
			["Start Date", escapeHtml(val(ms.start_date))],
			["End Date", escapeHtml(val(ms.end_date))],
			["Duration", plan.duration_days ? `${plan.duration_days} days` : "—"],
			["Plan Fee", escapeHtml(formatMoney(plan.fee))],
			["Amount Paid", escapeHtml(formatMoney(ms.amount))],
			["Payment Ref.", escapeHtml(val(ms.payment_reference))],
			plan.description ? ["Description", escapeHtml(val(plan.description))] : null,
			ms.remarks ? ["Membership Notes", escapeHtml(val(ms.remarks))] : null,
		]);
	}

	function trainerCard(trainer) {
		if (!trainer) {
			return infoCard("Trainer", [["Assigned Trainer", `<span class="muted">Not assigned</span>`]]);
		}
		return infoCard("Trainer", [
			["Name", `<strong>${escapeHtml(val(trainer.trainer_name))}</strong>`],
			["Status", `<span class="status-pill ${trainer.status === "Active" ? "ok" : ""}">${escapeHtml(val(trainer.status))}</span>`],
			["Mobile", escapeHtml(val(trainer.mobile_no))],
			["Email", escapeHtml(val(trainer.email))],
			["Specialization", escapeHtml(val(trainer.specialization))],
			trainer.remarks ? ["Notes", escapeHtml(val(trainer.remarks))] : null,
		]);
	}

	function profileCard(m) {
		return infoCard("Member Details", [
			["Member ID", escapeHtml(val(m.name))],
			["Status", `<span class="status-pill ${m.status === "Active" ? "ok" : ""}">${escapeHtml(val(m.status))}</span>`],
			["Join Date", escapeHtml(val(m.join_date))],
			["Mobile", escapeHtml(val(m.mobile_no))],
			["Email", escapeHtml(val(m.email))],
			["Gender", escapeHtml(val(m.gender))],
			["Date of Birth", escapeHtml(val(m.date_of_birth))],
			m.remarks ? ["Remarks", escapeHtml(val(m.remarks))] : null,
		]);
	}

	function contactCard(m) {
		return infoCard("Contact & Emergency", [
			["Address", escapeHtml(val(m.address))],
			["Emergency Contact", escapeHtml(val(m.emergency_contact_name))],
			["Emergency Phone", escapeHtml(val(m.emergency_contact_phone))],
		]);
	}

	function membershipHistoryHtml(memberships) {
		if (!memberships || !memberships.length) return "";
		const rows = memberships
			.map((ms) => {
				const plan = ms.plan ? ms.plan.plan_name || ms.membership_plan : ms.membership_plan;
				return `
				<div class="att-row">
					<strong>${escapeHtml(plan)}</strong>
					<span class="status-pill small ${ms.status === "Active" ? "ok" : ""}">${escapeHtml(ms.status)}</span>
					<p class="muted" style="margin:6px 0 0">${escapeHtml(ms.start_date)} → ${escapeHtml(ms.end_date || "—")} · ${escapeHtml(formatMoney(ms.amount))}</p>
				</div>
			`;
			})
			.join("");
		return `<p class="section-title">Membership History</p>${rows}`;
	}

	async function renderMemberDetail(name) {
		$("#page-title").textContent = "Member";
		main.innerHTML = `<div class="loading">Loading…</div>`;
		const m = await api("gym_management.api.mobile.get_member", { gym_member: name });
		state.memberDetail = m;

		const attendanceHtml =
			m.attendance && m.attendance.length
				? m.attendance
						.map((a) => {
							const loc =
								a.check_in_latitude && a.check_in_longitude
									? `<p class="muted" style="margin:8px 0 0">📍 ${Number(a.check_in_latitude).toFixed(5)}, ${Number(a.check_in_longitude).toFixed(5)}</p>`
									: "";
							return `
				<div class="att-row">
					<strong>${escapeHtml(a.attendance_date)}</strong>
					${attendanceTimesHtml(a)}
					${loc}
				</div>
			`;
						})
						.join("")
				: `<p class="muted">No attendance records</p>`;

		const todayAttHtml =
			m.today_attendance && m.today_attendance.check_in_time
				? infoCard("Today's Attendance", [
						["Date", escapeHtml(val(state.config?.today || "Today"))],
						[
							"Check-in Time",
							`<strong>${escapeHtml(formatTime(m.today_attendance.check_in_time))}</strong>`,
						],
						[
							"Check-out Time",
							m.today_attendance.check_out_time
								? `<strong>${escapeHtml(formatTime(m.today_attendance.check_out_time))}</strong>`
								: `<span class="muted">Not yet</span>`,
						],
						m.today_attendance.check_out_time
							? [
									"Duration",
									escapeHtml(
										formatDuration(
											m.today_attendance.check_in_time,
											m.today_attendance.check_out_time
										) || "—"
									),
								]
							: null,
					])
				: "";

		main.innerHTML = `
			<button type="button" class="back-link" id="btn-back">← Back</button>
			<div class="detail-hero">
				<div class="avatar">${memberAvatar(m)}</div>
				<h2>${escapeHtml(m.member_name)}</h2>
				<p class="sub">${escapeHtml(m.mobile_no || m.name)}</p>
				<span class="status-pill ${m.status === "Active" ? "ok" : ""}">${escapeHtml(m.status)}</span>
				${
					m.today_attendance && m.today_attendance.check_in_time
						? `<p class="today-time">Today: In ${escapeHtml(formatTime(m.today_attendance.check_in_time))}${
								m.today_attendance.check_out_time
									? ` · Out ${escapeHtml(formatTime(m.today_attendance.check_out_time))}`
									: ""
							}</p>`
						: ""
				}
			</div>
			<div class="detail-actions">
				${
					!m.checked_in_today
						? `<button class="btn btn-primary btn-block" id="btn-checkin">Check In</button>`
						: ""
				}
				${
					m.checked_in_today &&
					m.today_attendance &&
					m.today_attendance.check_in_time &&
					!m.today_attendance.check_out_time
						? `<button class="btn btn-checkout btn-block" id="btn-checkout">Check Out</button>`
						: ""
				}
				${
					m.today_attendance && m.today_attendance.check_out_time
						? `<button class="btn btn-secondary btn-block" disabled>Completed for today</button>`
						: ""
				}
			</div>
			${todayAttHtml}
			${profileCard(m)}
			${membershipCard(m.membership)}
			${trainerCard(m.trainer)}
			${contactCard(m)}
			${membershipHistoryHtml(m.memberships)}
			<p class="section-title">Recent Attendance</p>
			${attendanceHtml}
		`;
		$("#btn-back").onclick = () => showView(state.view);
		const checkInBtn = $("#btn-checkin");
		if (checkInBtn) checkInBtn.onclick = () => doCheckIn(name);
		const checkOutBtn = $("#btn-checkout");
		if (checkOutBtn) {
			checkOutBtn.onclick = () =>
				doCheckOut(m.today_attendance.name, name);
		}
	}

	async function doCheckIn(gymMember) {
		const coords = await getLocation();
		if (!coords) showToast("GPS unavailable — saving without location", "warn");
		try {
			const r = await api("gym_management.api.mobile.check_in", {
				gym_member: gymMember,
				...coords,
			});
			showToast(r.message || "Checked in!", "success");
			if (state.memberDetail?.name === gymMember) {
				renderMemberDetail(gymMember);
			} else {
				showView(state.view);
			}
		} catch (e) {
			showToast(e.message, "warn");
		}
	}

	async function doCheckOut(attendanceLog, gymMember) {
		const coords = await getLocation();
		if (!coords) showToast("GPS unavailable — saving without location", "warn");
		try {
			const r = await api("gym_management.api.mobile.check_out", {
				attendance_log: attendanceLog,
				...coords,
			});
			showToast(r.message || "Checked out!", "success");
			if (state.memberDetail?.name === gymMember) {
				renderMemberDetail(gymMember);
			} else {
				showView(state.view);
			}
		} catch (e) {
			showToast(e.message, "warn");
		}
	}

	function bindMemberClicks(containerSel) {
		const el = document.querySelector(containerSel);
		el.querySelectorAll(".member-card").forEach((card) => {
			card.addEventListener("click", (e) => {
				if (e.target.closest("[data-checkin]")) {
					e.stopPropagation();
					doCheckIn(e.target.closest("[data-checkin]").dataset.checkin);
					return;
				}
				if (e.target.closest("[data-checkout]")) {
					e.stopPropagation();
					const btn = e.target.closest("[data-checkout]");
					doCheckOut(btn.dataset.checkout, btn.dataset.member);
					return;
				}
				renderMemberDetail(card.dataset.member);
			});
		});
	}

	function showView(view) {
		state.view = view;
		document.querySelectorAll(".tab").forEach((t) => {
			t.classList.toggle("active", t.dataset.view === view);
		});
		if (view === "home") renderHome();
		else if (view === "members") renderMembers();
		else if (view === "attendance") renderAttendance();
	}

	function debounce(fn, ms) {
		let t;
		return (...args) => {
			clearTimeout(t);
			t = setTimeout(() => fn(...args), ms);
		};
	}

	function escapeHtml(s) {
		const d = document.createElement("div");
		d.textContent = s || "";
		return d.innerHTML;
	}

	function registerServiceWorker() {
		if (!("serviceWorker" in navigator)) return;
		navigator.serviceWorker.register("/assets/gym_management/gym_pwa/sw.js").catch(() => {});
	}

	// Events
	$("#login-form").addEventListener("submit", async (e) => {
		e.preventDefault();
		const err = $("#login-error");
		err.classList.add("hidden");
		try {
			await login($("#login-user").value.trim(), $("#login-password").value);
			await bootApp();
		} catch (ex) {
			err.textContent = ex.message || "Login failed";
			err.classList.remove("hidden");
		}
	});

	$("#btn-logout").addEventListener("click", logout);

	document.querySelectorAll(".tab").forEach((tab) => {
		tab.addEventListener("click", () => showView(tab.dataset.view));
	});

	// Session check on load
	(async function init() {
		try {
			const logged = await fetch(`${API}/frappe.auth.get_logged_user`, {
				credentials: "include",
				headers: { "X-Frappe-CSRF-Token": window.gym_pwa.csrf_token },
			}).then((r) => r.json());
			if (logged.message && logged.message !== "Guest") {
				await bootApp();
			}
		} catch (e) {
			/* stay on login */
		}
	})();
})();
